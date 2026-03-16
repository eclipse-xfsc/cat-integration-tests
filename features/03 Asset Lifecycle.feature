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
