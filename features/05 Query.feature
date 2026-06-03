@domain.query @baseline
Feature: Query
  As a Federated Catalogue API consumer
  I want to query the catalogue using whichever query language the active graph backend supports
  So that I can discover credentials stored in the graph

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke @req.CAT-FR-CO-01 @cfg.default
  Scenario: openCypher query works against the Neo4j backend
    # Default profile: signatures off, gaiax off. Switch the active backend to Neo4j
    # in-process (no restart), upload an unsigned credential, and confirm its claims
    # are queryable via openCypher. The backend is restored to the default afterwards.
    Given the active graph backend is NEO4J
      And credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
    When execute openCypher query
      """
      MATCH (n:LegalPerson) RETURN n.uri LIMIT 10
      """
    Then get http 200:Success code
      And query result contains "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
    Then the original graph backend is restored

  @smoke @req.CAT-FR-CO-01 @cfg.default
  Scenario: SPARQL query works against the Fuseki backend
    # Same unsigned credential, queried via SPARQL-star (the Fuseki query language).
    # Fuseki is the default backend, so this scenario also leaves the stack on the
    # default graph database.
    Given the active graph backend is FUSEKI
      And credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
    When execute SPARQL query
      """
      PREFIX cred: <https://www.w3.org/2018/credentials#>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      PREFIX gx: <https://w3id.org/gaia-x/2511#>
      SELECT ?person WHERE {
        <<(?person rdf:type gx:LegalPerson)>> cred:credentialSubject ?cs .
      }
      LIMIT 10
      """
    Then get http 200:Success code
      And query result contains "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"
    Then the original graph backend is restored

  @smoke @cfg.strict @cfg.test-sig @wip
  Scenario: Query uploaded credential by credential subject
    # TODO: remove @wip when OpenCypher queries are supported on the deployed graph backend (Fuseki uses SPARQL, not OpenCypher).
    # Strict profile: full verification chain. Loire JWT fixture required.
    Given credential from fixture "loire/valid/participant-vp.loire.signed.jwt" is not uploaded
    When add credential from fixture "loire/valid/participant-vp.loire.signed.jwt" with content-type "application/vp+jwt"
    Then get http 201:Created code
    When execute openCypher query
      """
      MATCH (n:LegalPerson) RETURN n.uri LIMIT 10
      """
    Then get http 200:Success code
      And query result contains "did:web:participant.example.com"
