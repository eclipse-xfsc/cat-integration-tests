@req.CAT-FR-GD-02
Feature: Non-Credential RDF Graph Extraction
  As a Data Provider
  I want to upload bare RDF documents without a VC/VP wrapper
  So that all contained triples are stored in the graph database

  Background:
    Given CAT Keycloak is up
    And saved Keycloak token
    And Federated Catalogue Server is up

  Scenario: Upload JSON-LD without credential wrapper is accepted
    Given asset from fixture "valid/rdf/simple.jsonld" is not uploaded
    When add asset from fixture "valid/rdf/simple.jsonld" with content-type "application/ld+json"
    Then get http 201:Created code

  Scenario: Upload Turtle RDF document is accepted
    Given asset from fixture "valid/rdf/simple.ttl" is not uploaded
    When add asset from fixture "valid/rdf/simple.ttl" with content-type "text/turtle"
    Then get http 201:Created code

  Scenario: Upload N-Triples document is accepted
    Given asset from fixture "valid/rdf/simple.nt" is not uploaded
    When add asset from fixture "valid/rdf/simple.nt" with content-type "application/n-triples"
    Then get http 201:Created code

  Scenario: Upload RDF/XML document is accepted
    Given asset from fixture "valid/rdf/simple.rdf" is not uploaded
    When add asset from fixture "valid/rdf/simple.rdf" with content-type "application/rdf+xml"
    Then get http 201:Created code

  Scenario: Non-credential JSON-LD triple is queryable in the graph via openCypher
    Given asset from fixture "valid/rdf/simple.jsonld" is not uploaded
    When add asset from fixture "valid/rdf/simple.jsonld" with content-type "application/ld+json"
    Then get http 201:Created code
    When execute openCypher query
      """
      MATCH (n) WHERE "http://example.org/item1" IN n.claimsGraphUri RETURN n.uri, n.name
      """
    Then query result contains "http://example.org/item1"
    And query result contains "Cloud Storage Service"

  # TODO: remove @wip once openCypher/Neo4j is no longer the default graph backend.
  # The SPARQL endpoint (application/sparql-query) requires a Fuseki-backed deployment.
  # Run this scenario manually with: behave --tags=@wip --no-skipped
  @wip
  Scenario: Non-credential JSON-LD triple is queryable in the graph via SPARQL
    Given asset from fixture "valid/rdf/simple.jsonld" is not uploaded
    When add asset from fixture "valid/rdf/simple.jsonld" with content-type "application/ld+json"
    Then get http 201:Created code
    When execute SPARQL query
      """
      SELECT ?s ?p ?o WHERE {
        <<(?s ?p ?o)>> <https://www.w3.org/2018/credentials#credentialSubject> ?assetIri .
        FILTER(?s = <http://example.org/item1>)
      }
      """
    Then query result contains "http://example.org/item1"
    And query result contains "http://example.org/name"
