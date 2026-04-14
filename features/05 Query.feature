@domain.query @baseline
Feature: Query
  As a Federated Catalogue API consumer
  I want to query the catalogue using openCypher
  So that I can discover credentails stored in the graph

  Background:
    Given CAT Keycloak is up
      And saved Keycloak token
      And Federated Catalogue Server is up

  @smoke @req.CAT-FR-CO-01 @cfg.default
  Scenario: Upload unsigned credential and query it without trust framework
    # Default profile: signatures off, gaiax off. An unsigned credential can be
    # uploaded and its claims are queryable in the graph — no trust infrastructure needed.
    Given credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld" is not uploaded
    When add credential from fixture "valid/default-only/gaiax-participant-correct-type.vp.jsonld"
    Then get http 201:Created code
    When execute openCypher query
      """
      MATCH (n:LegalPerson) RETURN n.uri LIMIT 10
      """
    Then get http 200:Success code
      And query result contains "did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"

  @smoke @cfg.strict @cfg.test-sig
  Scenario: Query uploaded credential by credential subject
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
