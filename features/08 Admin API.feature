@domain.admin @req.CAT-FR-AU-01
Feature: Admin API — Runtime Configuration
  As a catalogue administrator
  I want to control schema validation and trust framework toggles at runtime
  So that the catalogue enforces the correct upload and verification policies without a restart

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @baseline @cfg.default
  Scenario: SHACL module disabled via admin API — violating credential accepted
    # Disable SHACL via admin API; a credential that violates a stored shape must still upload.
    Given schema from fixture "schemas/participant-requires-legalname.shacl.ttl" is uploaded
      And SHACL schema module is disabled
      And credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
      And SHACL schema module is re-enabled
      And uploaded schemas are cleaned up

  @baseline @cfg.strict
  Scenario: SHACL module re-enabled via admin API — violating credential rejected
    # Re-enable SHACL (default for strict); credential missing gx:legalName is rejected.
    Given schema from fixture "schemas/participant-requires-legalname.shacl.ttl" is uploaded
      And SHACL schema module is enabled
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 422:Unprocessable Entity code
      And uploaded schemas are cleaned up

  @baseline
  Scenario: SHACL module disabled — on-demand validation rejected with module_disabled
    # The on-demand validation gate fires before any asset lookup, so the rejection
    # is observable with placeholder asset ids and is independent of the
    # verifySchema server config.
    Given SHACL schema module is disabled
    When validate 2 dummy assets against all schemas
    Then get http 400:Bad Request code
      And response body contains "module_disabled:SHACL"
      And SHACL schema module is re-enabled

  @baseline @cfg.default
  Scenario: SHACL module disabled — credential verification with schema check rejected
    # The SHACL gate in CredentialVerificationStrategy fires when verifySchema=true
    # is passed explicitly via query param, so this scenario is independent of the
    # server's verifySchema default config.
    Given SHACL schema module is disabled
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" with schema check skipping signatures
    Then get http 400:Bad Request code
      And response body contains "module_disabled:SHACL"
      And SHACL schema module is re-enabled

  @baseline @cfg.default
  Scenario: OWL module disabled — custom-subclass credential fails role resolution with 400
    # resolveRole skips the rdfs:subClassOf+ walk when OWL is off. With verifySemantics
    # off (default config), the request reaches the unconditional null-role check in
    # VerificationServiceImpl, which rejects with 400 "not resolvable". In strict
    # config the same custom-subclass credential is rejected one layer earlier with
    # 422 "Semantic Error" (hasClasses() = false because the role resolves to UNKNOWN).
    # Both outcomes demonstrate the OWL toggle's effect; this scenario pins the 400
    # contract observable in default config.
    Given schema from fixture "schemas/ex-custom-participant.ontology.ttl" is uploaded as "text/turtle"
      And OWL schema module is disabled
    When verify credential from fixture "valid/default-only/custom-participant-subclass.vp.jsonld" skipping signatures
    Then get http 400:Bad Request code
      And response body contains "not resolvable"
      And OWL schema module is re-enabled
      And uploaded schemas are cleaned up

  @baseline
  Scenario: OWL module enabled — custom-subclass credential resolves via subclass walk
    # With OWL on, the same credential's type resolves to gx:Participant through the
    # rdfs:subClassOf+ walk in ClaimValidator.resolveViaOntology.
    Given schema from fixture "schemas/ex-custom-participant.ontology.ttl" is uploaded as "text/turtle"
      And OWL schema module is enabled
    When verify credential from fixture "valid/default-only/custom-participant-subclass.vp.jsonld" skipping signatures
    Then get http 200:Success code
      And uploaded schemas are cleaned up

  @baseline
  Scenario: OWL module disabled — registry-direct type still resolves
    # Control case: gx:LegalPerson is in the bundled Gaia-X 2511 ontology and indexed
    # at startup (tier 1), so it resolves regardless of the OWL toggle state.
    Given OWL schema module is disabled
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code
      And OWL schema module is re-enabled

  @smoke @cfg.default
  Scenario: Gaia-X trust framework disabled — compliance check skipped
    # With Gaia-X disabled, verification of a credential without compliance proof passes.
    Given Gaia-X trust framework is disabled
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @baseline @cfg.strict @cfg.test-sig
  Scenario: Gaia-X trust framework enabled — credential with valid trust anchor accepted
    # Full Gaia-X validation: type check + x5u + Trust Anchor Registry call → 201.
    Given Gaia-X trust framework is enabled
      And credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code
      And credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
      And Gaia-X trust framework is disabled

  @baseline @cfg.strict
  Scenario: Gaia-X trust framework enabled — credential with unrecognized type rejected
    # Credential subject type (legacy participant# namespace) is not in the recognized base class URIs
    # → hasClasses() = false → 422 Unprocessable Entity.
    Given Gaia-X trust framework is enabled
    When add credential from fixture "valid/default-only/gaiax-participant-legacy-type.vp.jsonld"
    Then get http 422:Unprocessable Entity code
      And Gaia-X trust framework is disabled

  @smoke @cfg.default
  Scenario: Admin stats endpoint returns all expected fields
    When request admin stats
    Then get http 200:Success code
      And response has admin stats fields

  @smoke
  Scenario: Ontology impact endpoint returns items array when no ontologies stored
    When request ontology impact list
    Then get http 200:Success code
      And response items is an array

  @baseline
  Scenario: Ontology impact endpoint surfaces contributions for an uploaded ontology
    # OntologyImpactService parses each ONTOLOGY-type row and counts the
    # rdfs:subClassOf+ descendants under each registered role root. The custom
    # ontology contributes one subclass (ex:MyCustomParticipant) to Participant.
    Given schema from fixture "schemas/ex-custom-participant.ontology.ttl" is uploaded as "text/turtle"
    When request ontology impact list
    Then get http 200:Success code
      And response items has at least 1 entry
      And response items contributions contain "Participant"
      And uploaded schemas are cleaned up

  @baseline
  Scenario: Ontology impact endpoint requires authentication
    # The /admin/schema-validation/** GET rule in SecurityConfig triggers the OAuth2
    # AuthenticationEntryPoint for anonymous requests, yielding 401 (other admin
    # endpoints land on AccessDeniedHandler → 403 because their rules differ).
    Given no auth token
    When request ontology impact list
    Then get http 401:Unauthorized code

  @baseline
  Scenario: Set schema module enabled rejects invalid module type with valid options listed
    # The path-variable enum on PUT /admin/schema-validation/modules/{type} rejects
    # values outside SHACL, JSON_SCHEMA, XML_SCHEMA, OWL. The error message lists
    # the accepted enum values so an admin client can correct the request.
    When set schema module "INVALID" to enabled
    Then get http 400:Bad Request code
      And response body contains "SHACL"
      And response body contains "JSON_SCHEMA"
      And response body contains "XML_SCHEMA"
      And response body contains "OWL"

  @baseline @cfg.default
  Scenario: All applicable validation modules disabled — on-demand validation rejected with 400
    # planAllApplicable falls through with no eligible strategy when SHACL, JSON
    # Schema, and XML Schema are all disabled. The reject is 400 ClientException
    # (aligned from the previous 422 VerificationException; see ADR 16) and the
    # message lists the modules an admin can enable to recover.
    Given SHACL schema module is disabled
      And JSON Schema module is disabled
      And XML Schema module is disabled
      And credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
      And save asset id from last response
    When validate saved asset against all schemas
    Then get http 400:Bad Request code
      And response body contains "No validation module is enabled or applicable"
      And SHACL schema module is re-enabled
      And JSON Schema module is re-enabled
      And XML Schema module is re-enabled

  # ---------------------------------------------------------------------------
  # Role Toggle
  #
  # Fixture notes:
  #   - service-offering.loire.signed.jwt  → type gx:ServiceOffering (direct role match)
  #   - digital-service-offering.loire.signed.jwt → type gx:DigitalServiceOffering
  #     (additional_root under ServiceOffering role in gaia-x-2511/framework.yaml)
  #   - participant.loire.signed.jwt → type gx:LegalPerson (Participant role — must stay active)
  #
  # OWL-subclass scenario is SKIPPED:
  #   No fixture exists for a credential whose @type is a runtime-uploaded OWL subclass of
  #   gx:ServiceOffering. Fabricating or signing a new fixture is out of scope here
  #   (see bdd-automation-knowledge/fixture-signing.md). Coverage is provided transitively by
  #   CredentialVerificationStrategyOwlToggleTest in fc-service-core.
  #
  # Persistence-across-restart is OUT OF SCOPE for this BDD suite.
  #   The JPA-backed unit tests in fc-service-core cover that guarantee transitively.
  # ---------------------------------------------------------------------------

  @baseline @cfg.strict @cfg.test-sig
  Scenario: Role disabled — ServiceOffering credential rejected (direct match)
    Given Gaia-X trust framework is enabled
      And role ServiceOffering of bundle gaia-x-2511 is disabled
      And credential from fixture "loire/valid/service-offering.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/service-offering.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 400:Bad Request code
      And response body contains "disabled"

  @baseline @cfg.strict @cfg.test-sig
  Scenario: Role disabled — DigitalServiceOffering credential rejected (additional_root)
    # gx:DigitalServiceOffering is an additional_root of ServiceOffering
    # in the gaia-x-2511 framework.yaml; disabling the role must also block this type.
    Given Gaia-X trust framework is enabled
      And role ServiceOffering of bundle gaia-x-2511 is disabled
      And credential from fixture "loire/valid/digital-service-offering.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/digital-service-offering.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 400:Bad Request code
      And response body contains "disabled"

  @baseline @cfg.strict @cfg.test-sig
  Scenario: Role disabled — other role (Participant) still accepted
    # disabling ServiceOffering must not affect the Participant role.
    # gx:LegalPerson is the root type for the Participant role in gaia-x-2511.
    Given Gaia-X trust framework is enabled
      And role ServiceOffering of bundle gaia-x-2511 is disabled
      And credential from fixture "loire/valid/participant.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code
      And credential from fixture "loire/valid/participant.loire.signed.jwt" is not uploaded

  @baseline @cfg.strict @cfg.test-sig
  Scenario: Re-enable role — previously rejected credential now accepted
    # after re-enabling ServiceOffering, the same credential succeeds.
    Given Gaia-X trust framework is enabled
      And role ServiceOffering of bundle gaia-x-2511 is disabled
      And role ServiceOffering of bundle gaia-x-2511 is re-enabled
      And credential from fixture "loire/valid/service-offering.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/service-offering.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code
      And credential from fixture "loire/valid/service-offering.loire.signed.jwt" is not uploaded

  @baseline @cfg.default
  Scenario: GET admin trust-frameworks returns role state for gaia-x-2511
    # GET /admin/trust-frameworks lists bundles with roles.
    # Default state: all roles enabled (true).
    Given Gaia-X trust framework is enabled
    When request admin trust frameworks
    Then get http 200:Success code
      And admin trust frameworks response includes bundle "gaia-x-2511" with role "ServiceOffering" enabled
