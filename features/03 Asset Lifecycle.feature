@domain.asset @baseline
Feature: Asset Lifecycle
  As a Federated Catalogue API consumer
  I want to manage Assets
  So that I can create, read, and revoke them

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke
  Scenario: List Assets
    When request list of assets
    Then get http 200:Success code

  # NOTE: 500 here means the FC server cannot authenticate to Keycloak's admin API.
  # The /participants endpoint calls Keycloak internally via client_credentials grant.
  # Check that KEYCLOAK_CREDENTIALS_SECRET in the catalogue environment matches the actual
  # "federated-catalogue" client secret in Keycloak (Clients → Credentials tab).
  @smoke @domain.participant
  Scenario: List Participants
    When request list of participants
    Then get http 200:Success code

  @smoke @domain.schema
  Scenario: List Schemas
    When request list of schemas
    Then get http 200:Success code

  # --- CAT-FR-AM-02: IRI-based asset retrieval ---

  @req.CAT-FR-AM-02 @cfg.default
  Scenario: Retrieve RDF asset by IRI
    # Upload a credential, extract the IRI from the 201 response, retrieve via GET /assets/{id}.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
    When get asset by id from last response
    Then get http 200:Success code

  @req.CAT-FR-AM-02 @cfg.default
  Scenario: Retrieve non-RDF asset by IRI returns 400
    # Non-RDF assets (PDF, binary) cannot be retrieved via GET /assets/{id} — raw content
    # download requires a dedicated endpoint (future story CAT-FR-SF-03).
    Given asset from fixture "valid/non-rdf/sample.pdf" is not uploaded
    When add asset from fixture "valid/non-rdf/sample.pdf" with content-type "application/pdf"
    Then get http 201:Created code
    When get asset by id from last response
    Then get http 400:Bad Request
