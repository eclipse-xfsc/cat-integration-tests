@domain.validation-storage @req.CAT-FR-CO-02
Feature: Validation Result Storage — Retrieval API
  As a catalogue user with appropriate permissions
  I want to retrieve stored validation results for assets
  So that I can track validation history and compliance status over time

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke
  Scenario: Get validation results for asset with no stored validations — returns empty list
    # Verify that requesting validations for an existing asset with no validation history
    # returns 200 with an empty list (not 404).
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
      And save asset id from last response
    When get validations for saved asset
    Then get http 200:Success code
      And response has empty list

  @baseline
  Scenario: Get validation results for non-existent asset — returns 404
    When get validations for asset "did:web:nonexistent.example.org"
    Then get http 404:Not Found code

  @baseline
  Scenario: Get single validation result by ID — returns 404 for non-existent ID
    # Validation result ID 999999 does not exist → 404.
    When get validation result by id 999999
    Then get http 404:Not Found code

  @smoke
  Scenario: Pagination parameters are respected for asset validations endpoint
    Given asset from fixture "valid/rdf/simple.jsonld" is not uploaded
    When add asset from fixture "valid/rdf/simple.jsonld" with content-type "application/ld+json"
    Then get http 201:Created code
      And save asset id from last response
    When get validations for saved asset with offset 0 and limit 10
    Then get http 200:Success code

