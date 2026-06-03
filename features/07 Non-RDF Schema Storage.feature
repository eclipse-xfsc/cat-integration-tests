@domain.schema @extended @req.CAT-FR-SF-01
Feature: Non-RDF Schema Storage
  As a user of the Federated Catalogue
  I want to upload, retrieve, list, and delete non-RDF schemas (JSON Schema, XML Schema)
  So that I can manage machine-readable schemas beyond RDF formats

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  # -- JSON Schema -----------------------------------------------------------

  Scenario: Upload a valid JSON Schema
    Given schema "schemas/person.schema.json" is cleaned up
    When upload schema from fixture "schemas/person.schema.json" with content-type "application/schema+json"
    Then get http 201:Created code
      And response has a schema id
      And response schema id is "https://example.org/schemas/person"

  Scenario: Retrieve uploaded JSON Schema by ID
    Given schema from fixture "schemas/person.schema.json" is uploaded as "application/schema+json"
    When get schema by response id
    Then get http 200:Success code
      And response body contains "$schema"
      And uploaded schemas are cleaned up

  Scenario: Delete an uploaded JSON Schema
    Given schema from fixture "schemas/person.schema.json" is uploaded as "application/schema+json"
    When delete schema by response id
    Then get http 200:Success code

  Scenario: Reject invalid JSON Schema with 422
    When upload schema from fixture "schemas/invalid.schema.json" with content-type "application/schema+json"
    Then get http 422:Unprocessable Entity code

  # -- XML Schema (XSD) ------------------------------------------------------

  Scenario: Upload a valid XML Schema
    Given schema "schemas/config.xsd" is cleaned up
    When upload schema from fixture "schemas/config.xsd" with content-type "application/xml"
    Then get http 201:Created code
      And response has a schema id
      And response schema id is "http://example.org/ns/config"

  Scenario: Retrieve uploaded XML Schema by ID
    Given schema from fixture "schemas/config.xsd" is uploaded as "application/xml"
    When get schema by response id
    Then get http 200:Success code
      And response body contains "xs:schema"
      And uploaded schemas are cleaned up

  Scenario: Delete an uploaded XML Schema
    Given schema from fixture "schemas/config.xsd" is uploaded as "application/xml"
    When delete schema by response id
    Then get http 200:Success code

  Scenario: Reject invalid XML Schema with 422
    When upload schema from fixture "schemas/invalid.xsd" with content-type "application/xml"
    Then get http 422:Unprocessable Entity code

  # -- Schema listing ---------------------------------------------------------

  Scenario: Uploaded JSON Schema appears in schema listing
    Given schema from fixture "schemas/person.schema.json" is uploaded as "application/schema+json"
    When request list of schemas
    Then get http 200:Success code
      And schema listing jsonSchemas contains "https://example.org/schemas/person"
      And uploaded schemas are cleaned up

  Scenario: Uploaded XML Schema appears in schema listing
    Given schema from fixture "schemas/config.xsd" is uploaded as "application/xml"
    When request list of schemas
    Then get http 200:Success code
      And schema listing xmlSchemas contains "http://example.org/ns/config"
      And uploaded schemas are cleaned up

  Scenario: Upload duplicate JSON Schema returns 409
    Given schema from fixture "schemas/person.schema.json" is uploaded as "application/schema+json"
    When upload schema from fixture "schemas/person.schema.json" with content-type "application/schema+json"
    Then get http 409:Conflict code
      And uploaded schemas are cleaned up

  # -- Versioning ---------------------------------------------

  @req.CAT-FR-SF-02
  Scenario: Retrieve previous schema version after update
    Given schema "schemas/person.schema.json" is cleaned up
    When upload schema from fixture "schemas/person.schema.json" with content-type "application/schema+json"
    Then get http 201:Created code
    When update schema from fixture "schemas/person.v2.schema.json" with content-type "application/json"
    Then get http 200:Success code
    When get schema by response id at version 1
    Then get http 200:Success code
      And response body contains "Person"
      And uploaded schemas are cleaned up
