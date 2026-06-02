import json
import uuid
import requests
from behave import when, then
from eu.xfsc.bdd.cat.components.fc_server import Server


class ContextType:
    fc_server: Server
    requests_response: requests.Response


_PROV_VC_ISSUER = "did:web:did-server"


def _build_provenance_vc(asset_id: str, version: int, predicate: str) -> str:
    """Build a minimal VC 2.0 provenance payload for the given asset version and PROV-O predicate."""
    return _build_provenance_vc_multi(asset_id, version, [predicate])


def _build_provenance_vc_multi(asset_id: str, version: int, predicates: list) -> str:
    """Build a VC 2.0 provenance payload that declares multiple PROV-O predicates on the same subject.

    Each predicate is assigned a distinct IRI object so that the projected graph carries a star of
    relations rather than a single repeated edge.
    """
    subject = {"id": f"{asset_id}:v{version}"}
    for idx, predicate in enumerate(predicates):
        local_name = predicate.split(":")[-1]
        subject[predicate] = f"{_PROV_VC_ISSUER}:{local_name}-{idx}"
    return json.dumps({
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "type": ["VerifiableCredential"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "issuer": _PROV_VC_ISSUER,
        "validFrom": "2026-01-01T00:00:00Z",
        "credentialSubject": subject,
    })


@when('add provenance credential for saved asset at version {version:d} with predicate "{predicate}"')
def add_provenance_for_saved_asset(context: ContextType, version: int, predicate: str) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    payload = _build_provenance_vc(context.last_asset_id, version, predicate)
    context.requests_response = context.fc_server.add_provenance_credential(
        context.last_asset_id, payload, version=version
    )


@when('add provenance credential for saved asset at version {version:d} with predicates "{predicates_csv}"')
def add_provenance_for_saved_asset_multi(context: ContextType, version: int, predicates_csv: str) -> None:
    """Add a single provenance credential whose credentialSubject carries several PROV-O predicates."""
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    predicates = [p.strip() for p in predicates_csv.split(",") if p.strip()]
    assert predicates, "predicates list must not be empty"
    payload = _build_provenance_vc_multi(context.last_asset_id, version, predicates)
    context.requests_response = context.fc_server.add_provenance_credential(
        context.last_asset_id, payload, version=version
    )


@when('cascade-delete saved asset by id')
def cascade_delete_saved_asset_by_id(context: ContextType) -> None:
    """Invoke DELETE /assets/by-id/{id} — idempotent cascade by asset IRI."""
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.delete_asset_by_id(context.last_asset_id)


@then('save provenance credential id from last response')
def save_provenance_credential_id_from_last_response(context: ContextType) -> None:
    body = context.requests_response.json()
    cred_id = body.get("credentialId")
    assert cred_id, f"Last response does not contain a 'credentialId' field: {body}"
    context.last_provenance_cred_id = cred_id


@when('list provenance credentials for saved asset')
def list_provenance_credentials_for_saved_asset(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.list_provenance_credentials(context.last_asset_id)


@when('list provenance credentials for saved asset at version {version:d}')
def list_provenance_credentials_for_saved_asset_at_version(context: ContextType, version: int) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.list_provenance_credentials(context.last_asset_id, version=version)


@when('get saved provenance credential')
def get_saved_provenance_credential(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id"
    assert hasattr(context, "last_provenance_cred_id"), "No saved provenance credential id — call 'save provenance credential id from last response' first"
    context.requests_response = context.fc_server.get_provenance_credential(
        context.last_asset_id, context.last_provenance_cred_id
    )


@when('verify saved provenance credential')
def verify_saved_provenance_credential(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id"
    assert hasattr(context, "last_provenance_cred_id"), "No saved provenance credential id — call 'save provenance credential id from last response' first"
    context.requests_response = context.fc_server.verify_provenance_credential(
        context.last_asset_id, context.last_provenance_cred_id
    )


@when('verify all provenance credentials for saved asset')
def verify_all_provenance_credentials_for_saved_asset(context: ContextType) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.verify_all_provenance_credentials(context.last_asset_id)


@then('save asset version count and latest version ordinal')
def save_asset_version_count_and_latest_version_ordinal(context: ContextType) -> None:
    body = context.requests_response.json()
    context.last_version_count = body.get("total")
    versions = body.get("versions", [])
    current = next((v["version"] for v in versions if v.get("isCurrent")), None)
    if current is None and versions:
        current = versions[0]["version"]
    context.last_current_version = current


@when('add provenance credential for saved asset at saved version with predicate "{predicate}"')
def add_provenance_for_saved_asset_at_saved_version(context: ContextType, predicate: str) -> None:
    assert hasattr(context, "last_asset_id"), "No saved asset id"
    assert hasattr(context, "last_current_version"), "No saved version ordinal — call 'save asset version count and latest version ordinal' first"
    payload = _build_provenance_vc(context.last_asset_id, context.last_current_version, predicate)
    context.requests_response = context.fc_server.add_provenance_credential(
        context.last_asset_id, payload, version=context.last_current_version
    )


@then('total version count is unchanged')
def total_version_count_is_unchanged(context: ContextType) -> None:
    assert hasattr(context, "last_version_count"), "No saved version count — call 'save asset version count and latest version ordinal' first"
    body = context.requests_response.json()
    total = body.get("total")
    assert total == context.last_version_count, \
        f"Expected total={context.last_version_count} (unchanged), got {total} — provenance add created a new version"


@then('save provenance credential count')
def save_provenance_credential_count(context: ContextType) -> None:
    body = context.requests_response.json()
    context.last_provenance_count = body.get("totalCount", 0)


@then('response has {n:d} more provenance credentials than before')
def response_has_n_more_provenance_credentials(context: ContextType, n: int) -> None:
    assert hasattr(context, "last_provenance_count"), "No saved count — call 'save provenance credential count' first"
    body = context.requests_response.json()
    total = body.get("totalCount")
    expected = context.last_provenance_count + n
    assert total == expected, f"Expected totalCount={expected} (baseline {context.last_provenance_count} + {n}), got {total}"


@then('response contains saved provenance credential')
def response_contains_saved_provenance_credential(context: ContextType) -> None:
    assert hasattr(context, "last_provenance_cred_id"), "No saved provenance credential id"
    body = context.requests_response.json()
    ids = [item.get("credentialId") for item in body.get("items", [])]
    assert context.last_provenance_cred_id in ids, \
        f"Saved credential id '{context.last_provenance_cred_id}' not found in listing: {ids}"


@then('response has {expected:d} provenance credentials')
def response_has_provenance_credentials(context: ContextType, expected: int) -> None:
    body = context.requests_response.json()
    total = body.get("totalCount")
    items = body.get("items", [])
    assert total == expected, f"Expected totalCount={expected}, got {total} in {body}"
    assert len(items) == expected, f"Expected {expected} items, got {len(items)} in {body}"


@then('provenance verification result is valid')
def provenance_verification_result_is_valid(context: ContextType) -> None:
    body = context.requests_response.json()
    is_valid = body.get("isValid")
    assert is_valid is True, f"Expected isValid=true, got: {body}"


@then('all provenance verification results are valid')
def all_provenance_verification_results_are_valid(context: ContextType) -> None:
    body = context.requests_response.json()
    is_valid = body.get("isValid")
    assert is_valid is True, f"Expected aggregated isValid=true, got: {body}"
