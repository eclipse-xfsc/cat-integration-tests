@domain.asset @req.CAT-FR-LM-01
Feature: Asset Version Control
  As a Federated Catalogue API consumer
  I want to update existing assets and retrieve specific historical versions
  So that I can audit changes over time

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @cfg.default
  Scenario: Upload asset, update to new version, retrieve latest and original version
    # SRS CAT-FR-LM-01 verification:
    # 1. Upload an asset.
    # 2. Upload a new version of the same asset.
    # 3. Retrieve the latest version and the original version of the asset.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
     And save asset id from last response
    When update saved asset with fixture "valid/version-control/gaiax-participant-v2.vp.jsonld"
    Then get http 200:Success code
    When get saved asset versions
    Then get http 200:Success code
     And response has 2 total versions
    When get saved asset
    Then get http 200:Success code
    When get saved asset at version 1
    Then get http 200:Success code
