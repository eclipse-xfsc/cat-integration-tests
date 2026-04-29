@domain.asset @extended
Feature: Credential Upload
  As a Federated Catalogue API consumer
  I want to upload Credentials without mandatory Gaia-X compliance
  So that the catalogue accepts credentials from any ecosystem

  # Default server config: gaiax.enabled=false, schema=false, semantics=true, signatures=true

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke @req.CAT-FR-CO-01 @cfg.default
  Scenario: Verification accepts credential without Gaia-X compliance
    # Credential has correct ontology @type but no Gaia-X compliance credential.
    # With gaiax.enabled=false (default), compliance check is skipped.
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @smoke @req.CAT-FR-CO-01
  Scenario: Invalid credential still rejected without compliance checks
    # client_error (400): no-triples check fires before compliance/schema/signature steps.
    When verify credential
      """
      { "invalid": "payload" }
      """
    Then get http 400:Bad Request code
    And response body contains "no triples"

  @req.CAT-FR-CO-01
  Scenario: Existing Gaia-X credential still passes verification
    # Backward compatibility: Gaia-X-typed credentials are not broken by
    # removal of mandatory compliance — they still verify successfully.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  # --- Strict config: upload with full validation (regression) ---

  @regression @cfg.strict
  Scenario: Upload rejects non-JWT credential with LD proof error
    # LD-proof VP (Ed25519Signature2020) — LD proof verification is not supported (CAT-TECH-01).
    When add credential from fixture "valid/ld-proof/participant-vp.ld-proof.jsonld"
    Then get http 422:Unprocessable Entity code

  @regression @cfg.strict @cfg.test-sig
  Scenario: Upload with valid signatures succeeds under strict config
    # Full end-to-end: JWT signature verification + trust anchor + schema + semantics → 201.
    Given credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code

  # --- CAT-FR-SF-04: No automatic SHACL validation on upload ---

  @req.CAT-FR-SF-04 @cfg.default
  Scenario: Upload credential that violates stored SHACL shape succeeds
    # Schema validation is disabled by default (verifySchema=false).
    # A SHACL shape requiring schema:legalName is in the schema store, but the
    # uploaded participant has no legalName. Upload must still return 201.
    Given schema from fixture "schemas/participant-requires-legalname.shacl.ttl" is uploaded
      And credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
      And uploaded schemas are cleaned up

  @req.CAT-FR-SF-04 @cfg.default
  Scenario: Upload response has empty validatorDids when signatures disabled
    # With signatures disabled (default), the upload response metadata
    # must not contain validator DIDs — no validation was performed.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
      And response has empty validatorDids

  @req.CAT-FR-SF-04 @cfg.strict @cfg.test-sig
  Scenario: Upload response has validatorDids under strict config
    # counterpart: With signatures enabled (strict), the upload response
    # must contain validator DIDs from the credential's proof objects.
    Given credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code
      And response has non-empty validatorDids

  @req.CAT-FR-SF-04 @cfg.strict
  Scenario: Upload credential that violates SHACL shape is rejected under strict config
    # With schema=true (strict config), SHACL validation IS enforced on upload.
    # The participant missing gx:legalName is rejected by the stored SHACL shape.
    Given schema from fixture "schemas/participant-requires-legalname.shacl.ttl" is uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 422:Unprocessable Entity code
      And uploaded schemas are cleaned up

  @req.CAT-FR-SF-04 @cfg.default
  Scenario: Verification passes for SHACL-violating credential when schema check disabled
    # The /verification endpoint skips SHACL when verifySchema=false.
    # A credential missing SHACL-required fields still passes verification.
    Given schema from fixture "schemas/participant-requires-legalname.shacl.ttl" is uploaded
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code
      And uploaded schemas are cleaned up
