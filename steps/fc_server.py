import hashlib
from pathlib import Path

import requests
from behave import given, when, then

from eu.xfsc.bdd.core.server.keycloak import KeycloakServer, Token

from eu.xfsc.bdd.cat.components.fc_server import Server

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class ContextType:
    fc_server: Server
    keycloak: KeycloakServer
    requests_response: requests.Response
    FileToken: Token


@given("Federated Catalogue Server is up")
def check_fc_server_up(context: ContextType) -> None:
    context.fc_server = Server(keycloak=context.keycloak)
    assert context.fc_server.is_up(), f"FC Server is not up at {context.fc_server.host}"


# -- Assets (credentials) --

@given('credential from fixture "{fixture_path}" is not uploaded')
def ensure_credential_not_uploaded(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    asset_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    resp = context.fc_server.delete_asset(asset_hash)
    assert resp.status_code in (200, 404), \
        f"Unexpected cleanup response: {resp.status_code}, {resp.content}"


@when("request list of assets")
def request_list_assets(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_assets()


@when('add credential')
def add_credential(context: ContextType) -> None:
    assert context.text, "Step requires docstring with credential payload"
    context.requests_response = context.fc_server.add_asset(context.text)


@when('add credential from fixture "{fixture_path}"')
def add_credential_from_fixture(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.add_asset(payload)


@when('get asset by id "{asset_id}"')
def get_asset_by_id(context: ContextType, asset_id: str) -> None:
    context.requests_response = context.fc_server.get_asset(asset_id)


@when('get asset by id from last response')
def get_asset_by_id_from_response(context: ContextType) -> None:
    """Extract asset ID from the last upload response and retrieve by IRI."""
    response_json = context.requests_response.json()
    asset_id = response_json.get("id")
    assert asset_id, f"Last response does not contain an 'id' field: {response_json}"
    context.requests_response = context.fc_server.get_asset(asset_id)


@when('delete asset "{asset_hash}"')
def delete_asset(context: ContextType, asset_hash: str) -> None:
    context.requests_response = context.fc_server.delete_asset(asset_hash)


@when('revoke asset "{asset_hash}"')
def revoke_asset(context: ContextType, asset_hash: str) -> None:
    context.requests_response = context.fc_server.revoke_asset(asset_hash)


# -- Verification --

@when("verify credential")
def verify_credential(context: ContextType) -> None:
    assert context.text, "Step requires docstring with credential payload"
    context.requests_response = context.fc_server.verify(context.text)


@when('verify credential from fixture "{fixture_path}"')
def verify_credential_from_fixture(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.verify(payload)


@when('verify credential from fixture "{fixture_path}" skipping signatures')
def verify_credential_from_fixture_skip_sigs(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.verify(payload, params={
        "verifyVPSignature": "false",
        "verifyVCSignature": "false",
    })


# -- Query --

@when('execute query "{statement}"')
def execute_query(context: ContextType, statement: str) -> None:
    context.requests_response = context.fc_server.query(statement)


@when("execute openCypher query")
def execute_opencypher_query(context: ContextType) -> None:
    assert context.text, "Step requires docstring with openCypher query"
    context.requests_response = context.fc_server.query(context.text, query_language="opencypher")


@then('response has empty validatorDids')
def response_has_empty_validator_dids(context: ContextType) -> None:
    body = context.requests_response.json()
    validators = body.get("validatorDids")
    assert not validators, \
        f"Expected empty or null validatorDids, got: {validators}"


@then('response has non-empty validatorDids')
def response_has_non_empty_validator_dids(context: ContextType) -> None:
    body = context.requests_response.json()
    validators = body.get("validatorDids", [])
    assert len(validators) > 0, \
        f"Expected non-empty validatorDids, got: {validators}"


@then('query result contains "{expected_value}"')
def query_result_contains(context: ContextType, expected_value: str) -> None:
    body = context.requests_response.json()
    items = body.get("items", [])
    flat = str(items)
    assert expected_value in flat, \
        f"Expected '{expected_value}' in query results, got: {items}"


# -- Schemas --

CONTENT_TYPE_MAP = {
    ".ttl": "text/turtle",
    ".jsonld": "application/ld+json",
    ".json": "application/json",
    ".rdf": "application/rdf+xml",
}


@given('schema from fixture "{fixture_path}" is uploaded')
def upload_schema_from_fixture(context: ContextType, fixture_path: str) -> None:
    path = FIXTURES_DIR / fixture_path
    payload = path.read_text()
    content_type = CONTENT_TYPE_MAP.get(path.suffix, "application/json")
    resp = context.fc_server.add_schema(payload, content_type=content_type)
    assert resp.status_code in (200, 201, 409), \
        f"Schema upload failed: {resp.status_code}, {resp.content}"
    # Track uploaded schema ID for cleanup
    if resp.status_code == 201 and "location" in resp.headers:
        schema_id = resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]
        try:
            context._uploaded_schema_ids.append(schema_id)
        except KeyError:
            context._uploaded_schema_ids = [schema_id]


@given('uploaded schemas are cleaned up')
@then('uploaded schemas are cleaned up')
def cleanup_uploaded_schemas(context: ContextType) -> None:
    try:
        schema_ids = context._uploaded_schema_ids
    except KeyError:
        schema_ids = []
    for schema_id in schema_ids:
        resp = context.fc_server.delete_schema(schema_id)
        assert resp.status_code in (200, 204, 404), \
            f"Schema cleanup failed for {schema_id}: {resp.status_code}, {resp.content}"
    context._uploaded_schema_ids = []


# -- Assets (non-RDF uploads) --

@given('asset from fixture "{fixture_path}" is not uploaded')
def ensure_asset_not_uploaded(context: ContextType, fixture_path: str) -> None:
    file_content = (FIXTURES_DIR / fixture_path).read_bytes()
    asset_hash = hashlib.sha256(file_content).hexdigest()
    resp = context.fc_server.delete_asset(asset_hash)
    assert resp.status_code in (200, 404), \
        f"Unexpected cleanup response: {resp.status_code}, {resp.content}"


@when('add asset from fixture "{fixture_path}" with content-type "{content_type}"')
def add_asset_multipart(context: ContextType, fixture_path: str, content_type: str) -> None:
    path = FIXTURES_DIR / fixture_path
    file_content = path.read_bytes()
    context.requests_response = context.fc_server.add_asset_multipart(
        file_content=file_content,
        content_type=content_type,
        filename=path.name,
    )


@when('add asset from fixture "{fixture_path}" as raw binary')
def add_asset_raw_binary(context: ContextType, fixture_path: str) -> None:
    path = FIXTURES_DIR / fixture_path
    file_content = path.read_bytes()
    context.requests_response = context.fc_server.add_asset_raw(
        file_content=file_content,
        content_type="application/octet-stream",
    )


@then('response content-type is "{expected_type}"')
def response_content_type_is(context: ContextType, expected_type: str) -> None:
    body = context.requests_response.json()
    actual = body.get("contentType")
    assert actual == expected_type, \
        f"Expected contentType '{expected_type}', got '{actual}' in {body}"


@then('response has file size greater than {minimum:d}')
def response_has_file_size_greater_than(context: ContextType, minimum: int) -> None:
    body = context.requests_response.json()
    file_size = body.get("fileSize")
    assert file_size is not None, f"Response missing fileSize field: {body}"
    assert file_size > minimum, \
        f"Expected fileSize > {minimum}, got {file_size}"


@when("request list of schemas")
def request_list_schemas(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_schemas()


# -- Participants --

@when("request list of participants")
def request_list_participants(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_participants()


# -- Session --

@when("request current session")
def request_current_session(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_session()
