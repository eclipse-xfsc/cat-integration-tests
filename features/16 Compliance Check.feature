@domain.compliance @req.CAT-FR-CO-05 @cfg.default
Feature: Compliance Check
  As a catalogue user
  I want to run a compliance check for an asset against a trust framework profile
  And retrieve stored compliance check results
  So that I can verify and track whether assets meet trust framework requirements

  Background:
    Given CAT Keycloak is up
    And saved Keycloak token
    And Federated Catalogue Server is up
    And mock trust framework is enabled

  @uses.compliance-mock
  Scenario: Compliance check with mismatched VP id — request reaches the clearing house
    # VP JWT id "did:web:compliance-asset.example.org" does not match the path asset id
    # "did:web:compliance-test.example.org". The orchestrator no longer short-circuits on
    # this mismatch — it forwards the request to the compliance service and returns whatever
    # the clearing house decides. The stub here is configured to issue an attestation, so
    # the result is conforms=true and the compliance service did receive a call.
    Given compliance service is stubbed to issue attestation
    When run compliance check for asset "did:web:compliance-test.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is true
    And compliance result has attestation credential
    And compliance service received 1 calls

  @uses.compliance-mock
  Scenario: Compliance check with non-JWT credential — client returns unverifiable without contacting service
    # A plain string is not a parseable JWT: orchestrator passes through (blank id = no mismatch),
    # then the GxdchComplianceClient finds no id claim and returns UNVERIFIABLE_ATTESTATION.
    Given compliance service is stubbed to issue attestation
    When run compliance check for asset "did:web:compliance-test.example.org" with profile "mock-2026" and credential "not-a-valid-jwt"
    Then get http 200:Success code
    And compliance result conforms is false
    And compliance result failure category is "UNVERIFIABLE_ATTESTATION"
    And compliance service received 0 calls

  @smoke
  Scenario: Stored compliance checks are retrievable after a compliance check
    # Self-contained: runs its own compliance check before retrieval.
    When run compliance check for asset "did:web:compliance-test.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    When get stored compliance checks for asset "did:web:compliance-test.example.org"
    Then get http 200:Success code
    And stored compliance checks list is not empty

  Scenario: Get stored compliance checks — pagination parameters are accepted
    When get stored compliance checks for asset "did:web:compliance-test.example.org" with offset 0 and limit 1
    Then get http 200:Success code
    And stored compliance checks list size is at most 1

  Scenario: Unknown framework profile — returns 400
    When run compliance check for asset "did:web:compliance-test.example.org" with profile "unknown-profile-xyz" and credential "any"
    Then get http 400:Bad Request code

  Scenario: Disabled trust framework family — returns 409
    # Asset id must match the VP JWT id so the orchestrator's id-mismatch short-circuit
    # is not hit first — only then is the disabled-family gate (409) reached.
    Given mock trust framework is disabled
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 409:Conflict code
    And mock trust framework is re-enabled

  # -----------------------------------------------------------------------
  # Live compliance service interaction (requires WireMock)
  # Set CAT_WIREMOCK_HOST and ensure FC server's mock-2026.service_url
  # points to the same WireMock instance before running these scenarios.
  # -----------------------------------------------------------------------

  @uses.compliance-mock @smoke
  Scenario: Compliance service issues attestation — returns conforms=true
    # VP id "did:web:compliance-asset.example.org" matches the path asset id: orchestrator passes through.
    # WireMock returns 201 with a parseable JWT → IssuedAttestation.
    Given compliance service is stubbed to issue attestation
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is true
    And compliance result has attestation credential

  @uses.compliance-mock
  Scenario: Compliance service rejects credential as non-compliant — returns conforms=false
    # WireMock returns 400: GxdchComplianceClient maps this to UnverifiableAttestation.
    Given compliance service is stubbed to reject as non-compliant
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is false
    And compliance result failure category is "UNVERIFIABLE_ATTESTATION"

  @uses.compliance-mock
  Scenario: Compliance service unavailable — FC returns 503
    # WireMock returns 503: orchestrator maps HttpServerErrorException to ServiceUnavailableException → 503.
    Given compliance service is stubbed to return service error
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 503:Service Unavailable code

  # -----------------------------------------------------------------------
  # Runtime bundle-config override (CAT-FR-CO-03 "configuring their unique identifiers")
  # Demonstrates that an operator-issued PATCH to /admin/trust-frameworks/bundles/{id}
  # immediately redirects subsequent compliance calls to the new endpoint identifier,
  # without restarting the catalogue server.
  # -----------------------------------------------------------------------

  @req.CAT-FR-CO-03 @uses.compliance-mock
  Scenario: Operator overrides bundle compliance path — next compliance call hits the new path
    # Both the YAML-default path and the new path are stubbed at WireMock.
    # After the operator's PATCH, the orchestrator must resolve the override
    # and route the credential POST to the new path; the YAML-default path
    # must receive zero calls for this scenario's check.
    Given compliance service is stubbed to issue attestation
    And compliance service is stubbed to issue attestation on path "/api/credential-offers/relocated-compliance"
    And operator overrides bundle "mock-2026" config: compliancePath = "/api/credential-offers/relocated-compliance"
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is true
    And compliance service received 1 calls on path "/api/credential-offers/relocated-compliance"
    And compliance service received 0 calls on path "/api/credential-offers/standard-compliance"

  @req.CAT-FR-CO-03 @uses.compliance-mock
  Scenario: Operator reverts the override — subsequent compliance call returns to YAML-default path
    # The PATCH override is applied, then explicitly cleared via JSON null.
    # The next compliance call must again hit the YAML-default path; the previously
    # overridden path must receive zero calls for this scenario's check.
    Given compliance service is stubbed to issue attestation
    And compliance service is stubbed to issue attestation on path "/api/credential-offers/relocated-compliance"
    And operator overrides bundle "mock-2026" config: compliancePath = "/api/credential-offers/relocated-compliance"
    And operator overrides bundle "mock-2026" config: compliancePath = "null"
    When run compliance check for asset "did:web:compliance-asset.example.org" with profile "mock-2026" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is true
    And compliance service received 1 calls on path "/api/credential-offers/standard-compliance"
    And compliance service received 0 calls on path "/api/credential-offers/relocated-compliance"
