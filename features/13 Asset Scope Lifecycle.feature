@domain.asset @req.CAT-FR-LM-04 @cfg.default
Feature: Asset Scope Lifecycle Management
  The management of an asset's lifecycle MUST cover, in addition to the asset itself,
  the human-readable representation linked to it.

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke
  Scenario: Linked human-readable representation is preserved on update and removed on delete
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
      And asset from fixture "valid/non-rdf/sample.pdf" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
     And save asset id from last response
    When upload human-readable from fixture "valid/non-rdf/sample.pdf" with content-type "application/pdf" for saved asset
    Then get http 201:Created code
     And save human-readable id from last response
    When get saved asset
    Then get http 200:Success code
     And response humanReadableId matches saved human-readable id
    When update saved asset with fixture "valid/version-control/gaiax-participant-v2.vp.jsonld"
    Then get http 200:Success code
    When get saved asset
    Then get http 200:Success code
     And response humanReadableId matches saved human-readable id
    When delete saved asset
    Then get http 200:Success code
    When get saved asset
    Then get http 404:Not Found
    When get saved human-readable asset
    Then get http 404:Not Found

  Scenario: Human-readable representation is accessible via link endpoint after asset update
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
      And asset from fixture "valid/non-rdf/sample.pdf" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
     And save asset id from last response
    When upload human-readable from fixture "valid/non-rdf/sample.pdf" with content-type "application/pdf" for saved asset
    Then get http 201:Created code
    When update saved asset with fixture "valid/version-control/gaiax-participant-v2.vp.jsonld"
    Then get http 200:Success code
    When get human-readable for saved asset
    Then get http 200:Success code
    When delete saved asset
    Then get http 200:Success code

  Scenario: Deleting an asset with no linked human-readable representation succeeds
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
     And save asset id from last response
    When delete saved asset
    Then get http 200:Success code
    When get saved asset
    Then get http 404:Not Found
