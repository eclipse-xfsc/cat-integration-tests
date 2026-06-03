@domain.auth @baseline
Feature: Authentication
  As a Federated Catalogue API consumer
  I need to authenticate via Keycloak
  So that I can access protected endpoints

  @smoke
  Scenario: Keycloak is reachable
    Given CAT Keycloak is up

    # NOTE: if this fails, you probably haven't created a user in keycloak. Don't forget to assign the needed cat roles as well. (Ro-*)
  @smoke
  Scenario: Obtain access token
    Given CAT Keycloak is up
    When fetch Keycloak token
    Then save Keycloak token

  # NOTE: 500 here means the FC server cannot authenticate to Keycloak's admin API.
  # Check that KEYCLOAK_CREDENTIALS_SECRET in the catalogue environment matches the actual
  # "federated-catalogue" client secret in Keycloak (Clients → Credentials tab).
  @smoke @domain.session
  Scenario: Access session with valid token
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up
    When request current session
    Then get http 200:Success code