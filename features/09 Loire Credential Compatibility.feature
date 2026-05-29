@domain.asset @req.CAT-FR-GD-01
Feature: Loire Credential Compatibility
  As a Federated Catalogue operator
  I want Loire-format Gaia-X credentials (ICAM 24.07 / W3C VC-JOSE-COSE) to be accepted
  So that the catalogue supports the current Gaia-X standard

  # Loire JWTs differ from VC 2.0 (danubetech path):
  #   - typ: vc+jwt / vp+jwt (W3C VC-JOSE-COSE headers)
  #   - Credential fields are TOP-LEVEL in JWT payload (no "vc"/"vp" wrapper claim)
  #   - Uses 2511 namespace (gx:LegalPerson instead of gax-core:Participant)
  #   - VP uses EnvelopedVerifiableCredential with data: URIs
  #
  # Signed fixtures are generated from .jsonld templates with:
  #   python3 scripts/generate-jwt-fixture.py --payload <template.jsonld> --key keys/jwt-signing.pem
  # Requires did-server with matching public key in assertionMethod.
  #
  # Sub-type fixtures (generate before running @cfg.strict sub-type scenarios):
  #   python3 scripts/generate-jwt-fixture.py \
  #       --payload fixtures/loire/valid/service-offering.loire.jsonld --key keys/jwt-signing.pem
  #   python3 scripts/generate-jwt-fixture.py \
  #       --payload fixtures/loire/valid/digital-service-offering.loire.jsonld --key keys/jwt-signing.pem

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke
  Scenario: Upload a Loire VC with W3C headers
    # Loire VC JWT: typ=vc+jwt, cty=vc, 2511 namespace, gx:LegalPerson type.
    # Tests the full pipeline: FormatDetector → LoireJwtParser → 2511 type resolution → storage.
    Given credential from fixture "loire/valid/participant.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code

  Scenario: Upload a Loire VP with EnvelopedVerifiableCredential
    # Loire VP JWT: typ=vp+jwt, cty=vp. Inner VC embedded as EnvelopedVerifiableCredential
    # with data:application/vc+jwt,<jwt> URI. Tests VP extraction + inner VC processing.
    Given credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code

  # --- EnvelopedVerifiableCredential / EnvelopedVerifiablePresentation (Gaia-X ICAM 24.07) ---
  #
  # EVC/EVP are JSON-LD wrapper objects with a data: URI carrying the JWT.
  # Unlike the compact JWT scenarios above, these are submitted as application/vc+ld+json
  # or application/vp+ld+json — the server must unwrap the data URI and verify the JWT.
  # Signature verification is mandatory: plain JSON-LD VPs have no JWS and must be rejected.

  @cfg.strict
  Scenario: Upload an EnvelopedVerifiableCredential wrapping a Loire VC JWT
    # EVC per Gaia-X ICAM 24.07: { "@context": "…/v2", "id": "data:application/vc+ld+json+jwt,<JWT>",
    # "type": "EnvelopedVerifiableCredential" }. Server unwraps the JWT and verifies the EdDSA signature.
    Given credential from fixture "enveloped/valid/participant.evc.jsonld" is not uploaded
    When add credential from fixture "enveloped/valid/participant.evc.jsonld" with content-type "application/vc+ld+json"
    Then get http 201:Created code

  @cfg.strict
  Scenario: Upload an EnvelopedVerifiablePresentation wrapping a Loire VP JWT
    # EVP per Gaia-X ICAM 24.07: { "@context": "…/v2", "id": "data:application/vp+ld+jwt,<JWT>",
    # "type": "EnvelopedVerifiablePresentation" }. Server unwraps the VP JWT and verifies the EdDSA signature.
    Given credential from fixture "enveloped/valid/participant.evp.jsonld" is not uploaded
    When add credential from fixture "enveloped/valid/participant.evp.jsonld" with content-type "application/vp+ld+json"
    Then get http 201:Created code

  @req.CAT-FR-GD-01 @cfg.strict
  Scenario: Verify an EnvelopedVerifiableCredential with valid signature
    # EVC submitted to /verification — server extracts and verifies the embedded Loire VC JWT.
    When verify credential from fixture "enveloped/valid/participant.evc.jsonld"
    Then get http 200:Success code
    And response has non-empty validatorDids

  @req.CAT-FR-GD-01 @cfg.strict
  Scenario: Verify an EnvelopedVerifiablePresentation with valid signature
    # EVP submitted to /verification — server extracts and verifies the embedded Loire VP JWT.
    When verify credential from fixture "enveloped/valid/participant.evp.jsonld"
    Then get http 200:Success code
    And response has non-empty validatorDids

  @cfg.strict
  Scenario: Loire VC 2.0 JSON-LD VP without JWT envelope is rejected in strict mode
    # Plain JSON-LD has no JWS proof — signature verification is impossible without a JWT.
    # Strict mode must reject rather than silently skip signature checks.
    When add credential from fixture "valid/inline-vp/participant-inline.vp.jsonld"
    Then get http 422:Unprocessable Entity code

  # --- Gaia-X ontology sub-type acceptance ---
  #
  # The FC resolves credential types through the gx: 2511 class hierarchy.
  # Any credential whose @type is a known subclass of gx:GaiaXEntity must be accepted.
  # These scenarios verify the full hierarchy path, not just the leaf type.

  @smoke @cfg.default
  Scenario: Upload a ServiceOffering credential
    # gx:ServiceOffering → gx:GaiaXEntity — direct sub-type of the root entity class.
    Given credential from fixture "loire/valid/service-offering.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/service-offering.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code

  @cfg.default
  Scenario: Upload a DigitalServiceOffering credential
    # gx:DigitalServiceOffering → gx:ServiceOffering → gx:GaiaXEntity —
    # two-level sub-type: verifies the FC resolves nested ontology hierarchy.
    Given credential from fixture "loire/valid/digital-service-offering.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/digital-service-offering.loire.signed.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code

  @req.CAT-FR-GD-01 @cfg.strict
  Scenario: Verify a ServiceOffering credential with valid signature
    When verify credential from fixture "loire/valid/service-offering.loire.signed.jwt"
    Then get http 200:Success code
    And response has non-empty validatorDids

  @req.CAT-FR-GD-01 @cfg.strict
  Scenario: Verify a DigitalServiceOffering credential with valid signature
    When verify credential from fixture "loire/valid/digital-service-offering.loire.signed.jwt"
    Then get http 200:Success code
    And response has non-empty validatorDids
