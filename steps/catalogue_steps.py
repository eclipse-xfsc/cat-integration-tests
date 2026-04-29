import hashlib
import json
import re
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from behave import given, when, then, use_step_matcher
from eu.xfsc.bdd.cat.components.fc_server import Server
from eu.xfsc.bdd.core.server.keycloak import KeycloakServer, Token
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class ContextType:
    fc_server: Server
    keycloak: KeycloakServer
    requests_response: requests.Response
    FileToken: Token

CONTENT_TYPE_MAP = {
    ".ttl": "text/turtle",
    ".jsonld": "application/ld+json",
    ".json": "application/json",
    ".rdf": "application/rdf+xml",
}

@given("Federated Catalogue Server is up")
def check_fc_server_up(context: ContextType) -> None:
    context.fc_server = Server(keycloak=context.keycloak)
    assert context.fc_server.is_up(), f"FC Server is not up at {context.fc_server.host}"


# -- Assets (credentials) --

####### Regex based matching for parser-ambiguous step definitions ######
use_step_matcher("re")

# behave could not match this step correctly and reported a duplicatestep definition, we fix it with a regex
@when(r'add credential from fixture "(?P<fixture_path>[^"]+)"')
def add_credential_from_fixture(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.add_asset(payload)

@when(r'verify credential from fixture "(?P<fixture_path>[^"]+)"')
def verify_credential_from_fixture(context: ContextType, fixture_path: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.verify(payload)


use_step_matcher("parse")

@given('credential from fixture "{fixture_path}" is not uploaded')
@then('credential from fixture "{fixture_path}" is not uploaded')
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

@when('add credential from fixture "{fixture_path}" with content-type "{content_type}"')
def add_credential_from_fixture_with_content_type(
        context: ContextType, fixture_path: str, content_type: str) -> None:
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.add_asset_with_content_type(payload, content_type)


@then('save asset id from last response')
def save_asset_id_from_last_response(context: ContextType) -> None:
    response_json = context.requests_response.json()
    asset_id = response_json.get("id")
    assert asset_id, f"Last response does not contain an 'id' field: {response_json}"
    context.last_asset_id = asset_id


@when('update saved asset with fixture "{fixture_path}"')
def update_saved_asset_from_fixture(context: ContextType, fixture_path: str) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    payload = (FIXTURES_DIR / fixture_path).read_text()
    context.requests_response = context.fc_server.update_asset(context.last_asset_id, payload)


@when('get saved asset')
def get_saved_asset(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.get_asset(context.last_asset_id)


@when('get saved asset at version {version:d}')
def get_saved_asset_at_version(context: ContextType, version: int) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.get_asset(context.last_asset_id, version=version)


@when('get saved asset versions')
def get_saved_asset_versions(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.get_asset_versions(context.last_asset_id)


@then('response has {expected:d} total versions')
def response_has_total_versions(context: ContextType, expected: int) -> None:
    body = context.requests_response.json()
    total = body.get("total")
    assert total == expected, f"Expected total={expected}, got {total} in {body}"


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


@when("execute SPARQL query")
def execute_sparql_query(context: ContextType) -> None:
    assert context.text, "Step requires docstring with SPARQL query"
    context.requests_response = context.fc_server.query(context.text, query_language="sparql")


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

def _extract_schema_id_from_response(resp: requests.Response) -> str | None:
    """Extract schema ID from a 201 response JSON body."""
    try:
        return resp.json().get("id")
    except Exception:
        return None


def _extract_schema_id_from_fixture(path: Path) -> str | None:
    """Extract schema ID from fixture file content (same logic the server uses)."""
    try:
        content = path.read_text()
        if path.suffix == ".json":
            return json.loads(content).get("$id")
        if path.suffix == ".xsd":
            root = ET.fromstring(content)
            return root.get("targetNamespace")
    except Exception:
        pass
    return None


def _extract_schema_id_from_conflict(resp: requests.Response) -> str | None:
    """Extract schema ID from a 409 conflict response body (server-generated hash ID)."""
    try:
        body = resp.json()
        msg = body.get("message", "")
        # e.g. "A schema with id <hash> already exists."
        if "schema with id" in msg and "already exists" in msg:
            parts = msg.split()
            idx = parts.index("id")
            return parts[idx + 1]
    except Exception:
        pass
    return None


def _url_encode_schema_id(schema_id: str) -> str:
    return urllib.parse.quote(schema_id, safe="")


def _track_schema_id(context: ContextType, schema_id: str | None) -> None:
    if not schema_id:
        return
    try:
        context._uploaded_schema_ids.append(schema_id)
    except (AttributeError, KeyError):
        context._uploaded_schema_ids = [schema_id]


@given('schema from fixture "{fixture_path}" is uploaded')
def upload_schema_from_fixture(context: ContextType, fixture_path: str) -> None:
    path = FIXTURES_DIR / fixture_path
    payload = path.read_text()
    content_type = CONTENT_TYPE_MAP.get(path.suffix, "application/json")
    schema_id = _extract_schema_id_from_fixture(path)

    resp = context.fc_server.add_schema(payload, content_type=content_type)
    if resp.status_code == 409:
        conflict_id = schema_id or _extract_schema_id_from_conflict(resp)
        if conflict_id:
            context.fc_server.delete_schema(_url_encode_schema_id(conflict_id))
            resp = context.fc_server.add_schema(payload, content_type=content_type)

    assert resp.status_code in (200, 201), \
        f"Schema upload failed: {resp.status_code}, {resp.content}"
    _track_schema_id(context, _extract_schema_id_from_response(resp) or schema_id)


@given('schema from fixture "{fixture_path}" is uploaded as "{content_type}"')
def upload_schema_from_fixture_with_ct(context: ContextType, fixture_path: str, content_type: str) -> None:
    path = FIXTURES_DIR / fixture_path
    payload = path.read_text()
    schema_id = _extract_schema_id_from_fixture(path)

    resp = context.fc_server.add_schema(payload, content_type=content_type)
    if resp.status_code == 409:
        conflict_id = schema_id or _extract_schema_id_from_conflict(resp)
        if conflict_id:
            # Already exists — delete and re-upload for a clean response
            encoded = _url_encode_schema_id(conflict_id)
            context.fc_server.delete_schema(encoded)
            resp = context.fc_server.add_schema(payload, content_type=content_type)

    assert resp.status_code in (200, 201), \
        f"Schema upload failed: {resp.status_code}, {resp.content}"
    context.requests_response = resp
    _track_schema_id(context, _extract_schema_id_from_response(resp) or schema_id)


@given('schema "{fixture_path}" is cleaned up')
def cleanup_schema_by_fixture(context: ContextType, fixture_path: str) -> None:
    """Delete schema by ID extracted from fixture content."""
    path = FIXTURES_DIR / fixture_path
    schema_id = _extract_schema_id_from_fixture(path)
    if schema_id:
        encoded = _url_encode_schema_id(schema_id)
        resp = context.fc_server.delete_schema(encoded)
        assert resp.status_code in (200, 204, 404), \
            f"Schema cleanup failed: {resp.status_code}, {resp.content}"


@given('uploaded schemas are cleaned up')
@then('uploaded schemas are cleaned up')
def cleanup_uploaded_schemas(context: ContextType) -> None:
    schema_ids = getattr(context, "_uploaded_schema_ids", [])
    for schema_id in schema_ids:
        encoded = _url_encode_schema_id(schema_id)
        resp = context.fc_server.delete_schema(encoded)
        assert resp.status_code in (200, 204, 404), \
            f"Schema cleanup failed for {schema_id}: {resp.status_code}, {resp.content}"
    context._uploaded_schema_ids = []


@when('upload schema from fixture "{fixture_path}" with content-type "{content_type}"')
def upload_schema_with_content_type(context: ContextType, fixture_path: str, content_type: str) -> None:
    path = FIXTURES_DIR / fixture_path
    payload = path.read_text()
    resp = context.fc_server.add_schema(payload, content_type=content_type)
    context.requests_response = resp
    if resp.status_code == 201:
        _track_schema_id(context, _extract_schema_id_from_response(resp))


@when("get schema by response id")
def get_schema_by_response_id(context: ContextType) -> None:
    schema_id = _extract_schema_id_from_response(context.requests_response)
    assert schema_id, f"No schema ID in response: {context.requests_response.text}"
    encoded = _url_encode_schema_id(schema_id)
    context.requests_response = context.fc_server.get_schema(encoded)


@when("get schema by response id at version {version:d}")
def get_schema_by_response_id_at_version(context: ContextType, version: int) -> None:
    schema_id = _extract_schema_id_from_response(context.requests_response)
    assert schema_id, f"No schema ID in response: {context.requests_response.text}"
    encoded = _url_encode_schema_id(schema_id)
    context.requests_response = context.fc_server.get_schema(encoded, version=version)


@when('update schema from fixture "{fixture_path}" with content-type "{content_type}"')
def update_schema_with_content_type(context: ContextType, fixture_path: str, content_type: str) -> None:
    path = FIXTURES_DIR / fixture_path
    payload = path.read_text()
    schema_id = _extract_schema_id_from_fixture(path)
    assert schema_id, f"Could not extract schema ID from fixture: {fixture_path}"
    encoded = _url_encode_schema_id(schema_id)
    context.requests_response = context.fc_server.update_schema(encoded, payload, content_type=content_type)


@when("delete schema by response id")
def delete_schema_by_response_id(context: ContextType) -> None:
    schema_id = _extract_schema_id_from_response(context.requests_response)
    assert schema_id, f"No schema ID in response: {context.requests_response.text[:200]}"
    encoded = _url_encode_schema_id(schema_id)
    context.requests_response = context.fc_server.delete_schema(encoded)


@then("response has a schema id")
def response_has_schema_id(context: ContextType) -> None:
    body = context.requests_response.json()
    schema_id = body.get("id")
    assert schema_id, f"Expected non-empty schema id, got: {body}"


@then('response schema id is "{expected_id}"')
def response_schema_id_is(context: ContextType, expected_id: str) -> None:
    body = context.requests_response.json()
    actual = body.get("id")
    assert actual == expected_id, \
        f"Expected schema id '{expected_id}', got '{actual}'"


@then('response body contains "{text}"')
def response_body_contains(context: ContextType, text: str) -> None:
    body = context.requests_response.text
    assert text in body, \
        f"Expected '{text}' in response body, got: {body[:300]}"


@then('schema listing jsonSchemas contains "{expected_id}"')
def schema_listing_json_schemas_contains(context: ContextType, expected_id: str) -> None:
    body = context.requests_response.json()
    schemas = body.get("jsonSchemas", [])
    assert expected_id in schemas, \
        f"Expected '{expected_id}' in jsonSchemas, got: {schemas}"


@then('schema listing xmlSchemas contains "{expected_id}"')
def schema_listing_xml_schemas_contains(context: ContextType, expected_id: str) -> None:
    body = context.requests_response.json()
    schemas = body.get("xmlSchemas", [])
    assert expected_id in schemas, \
        f"Expected '{expected_id}' in xmlSchemas, got: {schemas}"


# -- Assets (non-RDF uploads) --

@given('asset from fixture "{fixture_path}" is not uploaded')
@then('asset from fixture "{fixture_path}" is not uploaded')
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


@when('upload human-readable from fixture "{fixture_path}" with content-type "{content_type}" for saved asset')
def upload_human_readable_for_saved_asset(context: ContextType, fixture_path: str, content_type: str) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    path = FIXTURES_DIR / fixture_path
    file_content = path.read_bytes()
    context.requests_response = context.fc_server.upload_human_readable(
        mr_id=context.last_asset_id,
        file_content=file_content,
        content_type=content_type,
        filename=path.name,
    )


@then('save human-readable id from last response')
def save_human_readable_id_from_last_response(context: ContextType) -> None:
    response_json = context.requests_response.json()
    hr_id = response_json.get("id")
    assert hr_id, f"Last response does not contain an 'id' field: {response_json}"
    context.last_hr_id = hr_id


@when('get human-readable for saved asset')
def get_human_readable_for_saved_asset(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.get_human_readable(context.last_asset_id)


@when('get saved human-readable asset')
def get_saved_human_readable_asset(context: ContextType) -> None:
    assert hasattr(context, "last_hr_id"), "No saved human-readable id — call 'save human-readable id from last response' first"
    context.requests_response = context.fc_server.get_asset(context.last_hr_id)


@then('response humanReadableId matches saved human-readable id')
def response_human_readable_id_matches(context: ContextType) -> None:
    assert hasattr(context, "last_hr_id"), "No saved human-readable id — call 'save human-readable id from last response' first"
    body = context.requests_response.json()
    actual = body.get("humanReadableId")
    assert actual == context.last_hr_id, \
        f"Expected humanReadableId '{context.last_hr_id}', got '{actual}' in {body}"


@then('response machineReadableId matches saved asset id')
def response_machine_readable_id_matches(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    body = context.requests_response.json()
    actual = body.get("machineReadableId")
    assert actual == context.last_asset_id, \
        f"Expected machineReadableId '{context.last_asset_id}', got '{actual}' in {body}"


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
