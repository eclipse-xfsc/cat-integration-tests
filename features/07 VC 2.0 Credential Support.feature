@domain.asset @req.CAT-FR-GD-01
Feature: VC 2.0 Credential Support
  As a Federated Catalogue API consumer
  I want to upload Verifiable Credentials in VC 2.0 format
  So that the catalogue accepts both VC 1.1 and VC 2.0 ecosystems

  # Default server config: verifyVCSignatures=false, verifyVPSignatures=false
  # VC 2.0 uses "validFrom" instead of "issuanceDate" and the v2 context URI.
  # Loire format: credential claims at top level, typ=vc+jwt (IANA), no vc/vp wrapper.

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke @cfg.default
  Scenario: Upload a standalone VC 2.0 credential
    # Loire JWT VC with gx:LegalPerson type. Signature not verified in default config.
    Given credential from fixture "loire/valid/participant.vc2.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant.vc2.jwt" with content-type "application/vc+jwt"
    Then get http 201:Created code

  @smoke @cfg.default
  Scenario: Upload a VC 2.0 credential wrapped in a Verifiable Presentation
    # JSON-LD VP wrapping an inline VC 2.0 credential with gx:LegalPerson type.
    Given credential from fixture "loire/valid/participant.vp2.jsonld" is not uploaded
    When add credential from fixture "loire/valid/participant.vp2.jsonld"
    Then get http 201:Created code

  @cfg.default
  Scenario: JWT body submitted with JSON-LD content-type is rejected
    # application/vc+ld+json expects JSON-LD, not a JWT compact serialization.
    Given credential from fixture "loire/valid/participant.vc2.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant.vc2.jwt" with content-type "application/vc+ld+json"
    Then get http 400:Bad Request code

  @cfg.default
  Scenario: JSON-LD body submitted with JWT content-type is rejected
    # application/vc+jwt expects a JWT compact serialization, not a JSON-LD document.
    Given credential from fixture "loire/valid/participant.vp2.jsonld" is not uploaded
    When add credential from fixture "loire/valid/participant.vp2.jsonld" with content-type "application/vc+jwt"
    Then get http 400:Bad Request code

  @cfg.default
  Scenario: VC 2.0 credential with expired validUntil is rejected
    # "validUntil" set to a past date — server must reject with 422.
    When add credential from fixture "vc20/invalid/participant-expired.vc2.jsonld"
    Then get http 422:Unprocessable Entity code

  @smoke @regression @cfg.default
  Scenario: VC 1.1 credential continues to be accepted after VC 2.0 support added
    # Backward compatibility: VC 1.1 fixture with "issuanceDate" must still succeed.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
