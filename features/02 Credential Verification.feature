@domain.verify @baseline
Feature: Credential Verification
  As a Federated Catalogue API consumer
  I want to verify a Credential
  So that I can check its validity before submitting it

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  # Smoke test: fixture uses legacy @type (http://w3id.org/gaia-x/participant#Participant)
  # which does not match any loaded ontology — server rejects with semantic error.
  @smoke @cfg.strict
  Scenario: Verify credential with unrecognised type returns semantic error
    When verify credential from fixture "valid/default-only/gaiax-participant-legacy-type.vp.jsonld"
    Then get http 422:Unprocessable Entity code

  @smoke @req.CAT-FR-CO-01 @cfg.default @cfg.strict
  Scenario: Verify credential with correct ontology type passes semantic check
    # Uses fixture with @type matching loaded ontology (https://w3id.org/gaia-x/core#Participant).
    # Signatures are skipped because the fixture is not signed.
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @smoke
  Scenario: Verify an invalid credential returns error
    When verify credential
      """
      { "invalid": "payload" }
      """
    Then get http 422:Unprocessable Entity code

  # --- Strict config: schema validation + Gaia-X enabled (regression) ---

  @smoke @regression @cfg.strict
  Scenario: Participant passes schema validation under strict config
    # Schema=true is active but the loaded SHACL shapes are permissive for this type.
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @regression @cfg.strict
  Scenario: Invalid payload rejected with schema validation enabled
    When verify credential
      """
      { "invalid": "payload" }
      """
    Then get http 422:Unprocessable Entity code

  @smoke @regression @cfg.strict
  Scenario: Verification passes with Gaia-X enabled but no compliance VC
    # FINDING: gaiax.enabled=true does NOT enforce compliance check on /verification.
    # The trust framework check is only enforced during upload (/assets).
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @regression @cfg.strict
  Scenario: Signature skip is allowed even under strict config
    # FINDING: strict config (gaiax=true, schema=true) does not prevent callers from
    # skipping signature verification via query params. The four verification flags
    # are orthogonal — no requirement mandates coupling them.
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" skipping signatures
    Then get http 200:Success code

  @smoke @regression @cfg.strict
  Scenario: Verification with valid signatures passes
    # Fixture signed with JsonWebSignature2020 + did:web.
    When verify credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.signed.jsonld"
    Then get http 200:Success code
