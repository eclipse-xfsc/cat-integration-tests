@domain.asset @req.CAT-FR-SF-03 @cfg.default
Feature: Asset Linking (Machine-Readable to Human-Readable)
  As an authorized user of the Federated Catalogue
  I want to link a human-readable representation to a machine-readable asset
  So that both representations are managed together and navigable

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  Scenario: SRS verification - upload MR asset, link HR representation, verify bidirectional references
    # SRS CAT-FR-SF-03 verification:
    # 1. Upload a machine-readable asset.
    # 2. Upload a human-readable representation for that asset.
    # 3. Present the asset - it contains a link to the human-readable representation.
    # 4. Present the human-readable representation - it contains a link back to the machine-readable asset.
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
    When get saved human-readable asset
    Then get http 200:Success code
     And response machineReadableId matches saved asset id
    Then credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
     And asset from fixture "valid/non-rdf/sample.pdf" is not uploaded

  Scenario: Requesting human-readable representation for asset without one returns not found
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
     And save asset id from last response
    When get human-readable for saved asset
    Then get http 404:Not Found
    Then credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
