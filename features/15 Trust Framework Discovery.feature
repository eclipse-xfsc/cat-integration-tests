@domain.trust-framework @req.CAT-FR-CO-03 @cfg.default
Feature: Trust Framework Discovery
  As a catalogue user
  I want to discover available trust frameworks and their profiles
  So that I can select the correct profile when submitting compliance checks

  Background:
    Given CAT Keycloak is up
    And saved Keycloak token
    And Federated Catalogue Server is up

  @smoke
  Scenario: List trust frameworks includes mock family with mock-2026 profile
    Given mock trust framework is enabled
    When request trust frameworks
    Then get http 200:Success code
    And response contains trust framework "mock" with profile "mock-2026"

  Scenario: Disabled trust framework family is excluded from listing
    Given mock trust framework is disabled
    When request trust frameworks
    Then get http 200:Success code
    And response does not contain trust framework "mock"
    And mock trust framework is re-enabled
