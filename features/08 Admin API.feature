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

  @baseline @cfg.strict
  Scenario: Gaia-X trust framework enabled — credential with unrecognized type rejected
    # Credential subject type (legacy participant# namespace) is not in the recognized base class URIs
    # → hasClasses() = false → 422 Unprocessable Entity.
    Given Gaia-X trust framework is enabled
    When add credential from fixture "valid/default-only/gaiax-participant-legacy-type.vp.jsonld"
    Then get http 422:Unprocessable Entity code

  @smoke @cfg.default
  Scenario: Admin stats endpoint returns all expected fields
    When request admin stats
    Then get http 200:Success code
      And response has admin stats fields
