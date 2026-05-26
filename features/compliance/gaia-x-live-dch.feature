@uses.live-gxdch @domain.compliance @req.CAT-FR-CO-04 @cfg.gaiax
Feature: Gaia-X Live DCH Compliance Check
  As a Federated Catalogue operator
  I want to run compliance checks against the live Gaia-X Digital Clearing House (Loire v2)
  So that Gaia-X participants can obtain verifiable compliance attestations from the real DCH

  # These scenarios require:
  #   - A QA stage with internet access to https://compliance.gaia-x.eu/v2
  #   - The gaia-x trust framework family enabled:
  #       PATCH /admin/trust-frameworks/gaia-x {"enabled":true}
  #       or env FEDERATED_CATALOGUE_ENABLED_TRUST_FRAMEWORKS=gaia-x
  #   - A signing key with a publicly resolvable x5u certificate chain trusted
  #     by the Gaia-X Trust Anchor registry (self-signed local CA not sufficient)
  #
  # Run with:
  #   behave --tags=uses.live-gxdch features/compliance/gaia-x-live-dch.feature
  #
  # NOT in default CI — tag-gated.

  Background:
    Given CAT Keycloak is up
    And saved Keycloak token
    And Federated Catalogue Server is up
    And Gaia-X trust framework is enabled

  @smoke @wip
  Scenario: Loire-conformant asset passes Live DCH compliance check
    # Precondition: gaia-x family enabled (Background).
    # Upload a Loire-conformant VP JWT signed with a key whose x5u chain is trusted
    # by the real Gaia-X Trust Anchor registry.
    #
    # FIXTURE: fixtures/loire/valid/participant-vp.loire.dch-trusted.signed.jwt
    # — NOT committed; must be provisioned for QA. Provisioning checklist:
    #   1. A real participant DID with x5u resolvable to a Gaia-X Trust Anchor chain.
    #   2. A JSON-LD payload (copy participant-vp.loire.jsonld; set `iss`/`issuer`
    #      to the real DID).
    #   3. Sign with the matching private key (algo per DCH spec; not Ed25519/
    #      did:web:did-server as in the negative-case fixture below).
    # Once the file is in place, drop @wip.
    Given credential from fixture "loire/valid/participant-vp.loire.dch-trusted.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.dch-trusted.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code
    And save asset id from last response
    When run compliance check for saved asset with profile "gaia-x-2511" and credential from fixture "loire/valid/participant-vp.loire.dch-trusted.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is true
    And compliance result has attestation credential
    And save attestation credential from last compliance response
    When execute SPARQL query
      """
      PREFIX fcmeta: <https://w3id.org/gaia-x/fcmeta#>
      SELECT ?check ?profileId ?validUntil WHERE {
        ?check a fcmeta:ComplianceCheck ;
               fcmeta:frameworkProfileId ?profileId ;
               fcmeta:credentialValidUntil ?validUntil .
      }
      """
    Then query result contains "gaia-x-2511"
    And compliance check SPARQL result has credentialValidUntil set

  Scenario: Non-conformant asset fails Live DCH compliance check with UNVERIFIABLE_ATTESTATION
    # A VP signed with a non-DCH-trusted key will be rejected by the live DCH.
    # The JwtVcComplianceClient maps any DCH rejection (4xx) to UNVERIFIABLE_ATTESTATION.
    # Fixture: fixtures/loire/valid/participant-vp.loire.signed.jwt (local test key,
    # not trusted by real DCH — produces the expected rejection).
    Given credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code
    And save asset id from last response
    When run compliance check for saved asset with profile "gaia-x-2511" and credential from fixture "loire/valid/participant-vp.loire.signed.jwt"
    Then get http 200:Success code
    And compliance result conforms is false
    And compliance result failure category is "UNVERIFIABLE_ATTESTATION"
