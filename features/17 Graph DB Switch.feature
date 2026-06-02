@domain.admin @req.CAT-FR-AU-01
Feature: Graph DB Admin — Live Backend Switch
  As a catalogue administrator
  I want to switch the active graph database backend in process and trigger rebuilds
  So that I can change the storage layer without restarting the server, and re-index
  RDF assets into the active graph when needed

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  # -------------------------------------------------------------------------
  # Container-lifecycle scenarios (cold-boot fallback, persistence across
  # `docker restart fc-server`, and reachability rejection that needs
  # `docker stop <backend>`) are intentionally NOT covered here — they
  # require shell-out to the Docker daemon from inside the test process.
  # Keep those manual or move to a docker-aware suite.
  # -------------------------------------------------------------------------

  @baseline @cfg.default @gate.merge
  Scenario: Switch endpoint applies the change live with no JVM restart
    # Verifies the core promise of the live-switch contract:
    # POST /admin/graph-database/switch performs an in-process swap, and the next
    # GET /admin/graph-database immediately reports the new activeBackend.
    Given the active graph backend is FUSEKI
    When switch graph backend to "NEO4J"
    Then get http 200:Success code
      And switch response message mentions the target backend
      And response has no restartRequired field
      And active graph backend is "NEO4J"
      And the original graph backend is restored

  @baseline @cfg.default @gate.merge
  Scenario: Status endpoint carries the live-switch shape
    # Asserts the API shape: preferredBackend and restartRequired must NOT appear
    # in the GET response. rdfAssetCount and the other live-switch fields must
    # be present.
    When request graph database status
    Then get http 200:Success code
      And graph database status has live-switch shape

  @baseline @cfg.default @gate.merge
  Scenario: Switch with unknown backend value is rejected
    # Invalid backend names must produce 400 with the accepted values listed in
    # the error message — the operator must be able to self-correct without
    # reading the source.
    When switch graph backend to "NOSQL"
    Then get http 400:Bad Request code
      And response message lists valid backends

  @baseline @cfg.default
  Scenario: Rebuild trigger completes asynchronously and re-indexes JWT-secured claims
    # POST /admin/graph/rebuild returns 202 Accepted (async kicked off) and the status
    # endpoint reports complete=true within the timeout. With a JWT VP uploaded first, the
    # rebuild must re-index its claims (errors=0 via the poll step, and the active-graph
    # claim count grows) — proving the rebuild path decodes JWT-secured credentials the
    # same way the upload path does.
    Given the active graph backend is FUSEKI
      And credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
      And the current graph claim count is recorded
      And a credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is uploaded with content-type "application/vp+jwt"
    When trigger graph rebuild
    Then get http 202:Accepted code
      And graph rebuild completes within timeout
      And the graph claim count grew beyond the recorded baseline

  @baseline @cfg.default
  Scenario: Rebuild while one is already running returns 409
    # A JWT VP fixture is uploaded first so the first rebuild has non-trivial work and the
    # second POST lands while it is still running, yielding a timing-stable 409. (Previously
    # deferred because a rebuild against an empty graph finished too fast to leave a window.)
    Given the active graph backend is FUSEKI
      And credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
      And a credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is uploaded with content-type "application/vp+jwt"
    When trigger graph rebuild
    Then get http 202:Accepted code
    When trigger graph rebuild
    Then get http 409:Conflict code
      And graph rebuild completes within timeout

  @baseline @cfg.default
  Scenario: Switch endpoint refuses callers without ADMIN_ALL
    # fc-restricted-test has only SCHEMA_READ — POST /admin/graph-database/switch
    # requires ADMIN_ALL. Keep the realm.json change history out of scope here;
    # we just rely on the existing restricted user.
    Given Keycloak token for user "fc-restricted-test" with password "CHANGE_ME_dev_only1"
    When switch graph backend to "NEO4J"
    Then get http 403:Forbidden code

  @baseline @cfg.default
  Scenario: Rebuild endpoint refuses callers without ADMIN_ALL
    Given Keycloak token for user "fc-restricted-test" with password "CHANGE_ME_dev_only1"
    When trigger graph rebuild
    Then get http 403:Forbidden code

  @baseline @cfg.default @gate.merge
  Scenario: Round-trip switch FUSEKI -> NEO4J -> FUSEKI
    # Asserts both directions of the swap with no intermediate restart and that
    # the backend state is correctly observable after each step.
    Given the active graph backend is FUSEKI
    When switch graph backend to "NEO4J"
    Then get http 200:Success code
      And active graph backend is "NEO4J"
    When switch graph backend to "FUSEKI"
    Then get http 200:Success code
      And active graph backend is "FUSEKI"

  @baseline @cfg.default
  Scenario: Switch to NONE disables the graph store
    # NONE is the explicit "no graph database" backend — DummyGraphStore takes over,
    # connected reports false, version string is the no-DB sentinel.
    Given the active graph backend is FUSEKI
    When switch graph backend to "NONE"
    Then get http 200:Success code
      And active graph backend is "NONE"
      And the original graph backend is restored

  @baseline @cfg.default
  Scenario: Switch endpoint refuses anonymous callers with 403
    # Spring Security routes anonymous (no-token) access on the admin graph
    # endpoints to AccessDeniedHandler, yielding 403 — same response shape as the
    # role-restricted case above. Asserting both makes a regression where one
    # path leaks past the other detectable.
    Given no auth token
    When switch graph backend to "NEO4J"
    Then get http 403:Forbidden code

  @baseline @cfg.default
  Scenario: Rebuild endpoint refuses anonymous callers with 403
    Given no auth token
    When trigger graph rebuild
    Then get http 403:Forbidden code

  @baseline @cfg.default
  Scenario: Rebuild on NONE backend returns 503
    # Per fc_openapi.yaml the rebuild endpoint reports Graph Store Disabled (503)
    # when the active backend is NONE. Validates the DummyGraphStore branch is
    # surfaced correctly through the rebuild path.
    Given the active graph backend is NONE
    When trigger graph rebuild
    Then get http 503:Service Unavailable code
      And the original graph backend is restored

