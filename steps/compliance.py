"""
Step definitions for trust framework discovery (CAT-FR-CO-03) and compliance checks (CAT-FR-CO-05).

WireMock-tagged scenarios (@uses.compliance-mock) require:
  - CAT_WIREMOCK_HOST pointing to a running WireMock instance
  - The FC server's mock-2026 service_url configured to the same WireMock host
"""
import os
from datetime import datetime
from pathlib import Path

import requests
from behave import given, then, when

GAIA_X_PROFILE_ID = "gaia-x-2511"

from eu.xfsc.bdd.cat.components.fc_server import Server

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

WIREMOCK_HOST = os.getenv("CAT_WIREMOCK_HOST", "http://localhost:8089")
COMPLIANCE_ENDPOINT_PATH = "/api/credential-offers/standard-compliance"
# Alternative path used by CAT-FR-CO-03 bundle-config override scenarios; the operator
# repoints the bundle's compliancePath to this URL at runtime, and the test verifies
# the next compliance call lands here rather than on COMPLIANCE_ENDPOINT_PATH.
RELOCATED_COMPLIANCE_ENDPOINT_PATH = "/api/credential-offers/relocated-compliance"

# Minimal unsecured JWT (alg:none, empty payload) used as mock attestation body.
# nimbusds JWTParser accepts PlainJWT; getJWTClaimsSet() returns {} with no exp → validUntil=null.
ATTESTATION_JWT = (FIXTURES_DIR / "mock-attestation.jwt").read_text().strip()


class ContextType:
    fc_server: Server
    requests_response: requests.Response


# ---------------------------------------------------------------------------
# Trust framework discovery
# ---------------------------------------------------------------------------

@when("request trust frameworks")
def request_trust_frameworks(context: ContextType) -> None:
    """GET /trust-frameworks"""
    context.requests_response = context.fc_server.get_trust_frameworks()


@then('response contains trust framework "{family_id}" with profile "{profile_id}"')
def response_contains_trust_framework_with_profile(
        context: ContextType, family_id: str, profile_id: str
) -> None:
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    entry = next((e for e in body if e.get("id") == family_id), None)
    assert entry is not None, \
        f"Trust framework '{family_id}' not found; ids present: {[e.get('id') for e in body]}"
    profiles = entry.get("profiles", [])
    assert profile_id in profiles, \
        f"Profile '{profile_id}' not in profiles {profiles} for family '{family_id}'"


@then('response does not contain trust framework "{family_id}"')
def response_does_not_contain_trust_framework(context: ContextType, family_id: str) -> None:
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    ids = [e.get("id") for e in body]
    assert family_id not in ids, \
        f"Trust framework '{family_id}' unexpectedly found in response ids: {ids}"


# ---------------------------------------------------------------------------
# Compliance check — request
# ---------------------------------------------------------------------------

@when('run compliance check for saved asset with profile "{profile}" '
      'and credential from fixture "{fixture_path}"')
def run_compliance_check_for_saved_asset_from_fixture(
        context: ContextType, profile: str, fixture_path: str
) -> None:
    """POST /assets/{id}/compliance-check — asset id from context.last_asset_id, credential from fixture."""
    assert hasattr(context, "last_asset_id"), \
        "No saved asset id — call 'save asset id from last response' first"
    credential = (FIXTURES_DIR / fixture_path).read_text().strip()
    context.requests_response = context.fc_server.run_compliance_check(
        context.last_asset_id, profile, credential
    )


@when('run compliance check for asset "{asset_id}" with profile "{profile}" '
      'and credential from fixture "{fixture_path}"')
def run_compliance_check_from_fixture(
        context: ContextType, asset_id: str, profile: str, fixture_path: str
) -> None:
    """POST /assets/{id}/compliance-check — credential body read from fixture file."""
    credential = (FIXTURES_DIR / fixture_path).read_text().strip()
    context.requests_response = context.fc_server.run_compliance_check(asset_id, profile, credential)


@when('run compliance check for asset "{asset_id}" with profile "{profile}" '
      'and credential "{credential}"')
def run_compliance_check_with_literal(
        context: ContextType, asset_id: str, profile: str, credential: str
) -> None:
    """POST /assets/{id}/compliance-check — credential passed as literal string."""
    context.requests_response = context.fc_server.run_compliance_check(asset_id, profile, credential)


# ---------------------------------------------------------------------------
# Compliance check — response assertions
# ---------------------------------------------------------------------------

@then("compliance result conforms is true")
def compliance_result_conforms_true(context: ContextType) -> None:
    body = context.requests_response.json()
    actual = body.get("conforms")
    assert actual is True, \
        f"Expected conforms=True, got {actual} in {body}"


@then("compliance result conforms is false")
def compliance_result_conforms_false(context: ContextType) -> None:
    body = context.requests_response.json()
    actual = body.get("conforms")
    assert actual is False, \
        f"Expected conforms=False, got {actual} in {body}"


@then('compliance result failure category is "{expected}"')
def compliance_result_failure_category(context: ContextType, expected: str) -> None:
    body = context.requests_response.json()
    actual = body.get("failureCategory")
    assert actual == expected, \
        f"Expected failureCategory='{expected}', got '{actual}' in {body}"


@then("compliance result has attestation credential")
def compliance_result_has_attestation_credential(context: ContextType) -> None:
    body = context.requests_response.json()
    credential = body.get("attestationCredential")
    assert credential, f"Expected non-empty attestationCredential in {body}"


@then("save attestation credential from last compliance response")
def save_attestation_credential(context: ContextType) -> None:
    """Save attestationCredential JWT from the last compliance check response for later assertions."""
    body = context.requests_response.json()
    credential = body.get("attestationCredential")
    assert credential, f"Expected non-empty attestationCredential in {body}"
    context.last_attestation_credential = credential


@then("compliance check SPARQL result has credentialValidUntil set")
def compliance_sparql_result_has_credential_valid_until(context: ContextType) -> None:
    """Assert SPARQL result row with frameworkProfileId='gaia-x-2511' has a credentialValidUntil
    value that parses as an xsd:dateTime (ISO 8601)."""
    body = context.requests_response.json()
    items = body.get("items", [])
    assert len(items) > 0, \
        f"SPARQL query returned no results — expected a fcmeta:ComplianceCheck node: {body}"

    def _binding_value(row: dict, *needles: str) -> str | None:
        for key, val in row.items():
            if any(n in key.lower() for n in needles):
                if isinstance(val, dict):
                    val = val.get("value")
                if val:
                    return str(val)
        return None

    for row in items:
        if not isinstance(row, dict):
            continue
        profile_id = _binding_value(row, "profileid")
        if profile_id != GAIA_X_PROFILE_ID:
            continue
        valid_until = _binding_value(row, "validuntil")
        assert valid_until, (
            f"Row for profileId='{GAIA_X_PROFILE_ID}' has no credentialValidUntil: {row}"
        )
        try:
            datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AssertionError(
                f"credentialValidUntil '{valid_until}' is not a valid xsd:dateTime: {exc}"
            ) from exc
        return

    raise AssertionError(
        f"No SPARQL result row found with frameworkProfileId='{GAIA_X_PROFILE_ID}': {items}"
    )


# ---------------------------------------------------------------------------
# Stored compliance checks
# ---------------------------------------------------------------------------

@when('get stored compliance checks for asset "{asset_id}"')
def get_stored_compliance_checks(context: ContextType, asset_id: str) -> None:
    """GET /assets/{id}/compliance-checks"""
    context.requests_response = context.fc_server.get_compliance_checks(asset_id)


@when('get stored compliance checks for asset "{asset_id}" with offset {offset:d} and limit {limit:d}')
def get_stored_compliance_checks_paginated(
        context: ContextType, asset_id: str, offset: int, limit: int
) -> None:
    """GET /assets/{id}/compliance-checks?offset=X&limit=Y"""
    context.requests_response = context.fc_server.get_compliance_checks(
        asset_id, params={"offset": offset, "limit": limit}
    )


@then("stored compliance checks list is not empty")
def stored_compliance_checks_not_empty(context: ContextType) -> None:
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    assert len(body) > 0, "Expected at least one stored compliance check result, got empty list"


@then("stored compliance checks list size is at most {n:d}")
def stored_compliance_checks_list_size_at_most(context: ContextType, n: int) -> None:
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    assert len(body) <= n, \
        f"Expected at most {n} stored compliance checks, got {len(body)} in {body}"


# ---------------------------------------------------------------------------
# WireMock stub helpers (@uses.compliance-mock scenarios only)
# ---------------------------------------------------------------------------

def _reset_wiremock() -> None:
    resp = requests.post(f"{WIREMOCK_HOST}/__admin/reset", timeout=5)
    resp.raise_for_status()


def _add_wiremock_stub(mapping: dict) -> None:
    resp = requests.post(f"{WIREMOCK_HOST}/__admin/mappings", json=mapping, timeout=5)
    resp.raise_for_status()


@given("compliance service is stubbed to issue attestation")
def stub_compliance_success(context) -> None:
    """WireMock returns 201 with a minimal valid JWT — maps to IssuedAttestation."""
    _reset_wiremock()
    _add_wiremock_stub({
        "request": {
            "method": "POST",
            "urlPathPattern": COMPLIANCE_ENDPOINT_PATH
        },
        "response": {
            "status": 201,
            "headers": {"Content-Type": "text/plain"},
            "body": ATTESTATION_JWT
        }
    })


@given("compliance service is stubbed to reject as non-compliant")
def stub_compliance_non_compliant(context) -> None:
    """WireMock returns 400 — GxdchComplianceClient maps this to UnverifiableAttestation."""
    _reset_wiremock()
    _add_wiremock_stub({
        "request": {
            "method": "POST",
            "urlPathPattern": COMPLIANCE_ENDPOINT_PATH
        },
        "response": {
            "status": 400,
            "body": "Non-compliant credential"
        }
    })


@given("compliance service is stubbed to return service error")
def stub_compliance_service_error(context) -> None:
    """WireMock returns 503 — orchestrator maps this to ServiceUnavailableException → HTTP 503."""
    _reset_wiremock()
    _add_wiremock_stub({
        "request": {
            "method": "POST",
            "urlPathPattern": COMPLIANCE_ENDPOINT_PATH
        },
        "response": {
            "status": 503,
            "body": "Service unavailable"
        }
    })


@then("compliance service received {n:d} calls")
def compliance_service_received_n_calls(context: ContextType, n: int) -> None:
    """Query WireMock's __admin/requests/count to verify POST call count to compliance endpoint."""
    resp = requests.post(
        f"{WIREMOCK_HOST}/__admin/requests/count",
        json={
            "method": "POST",
            "urlPathPattern": COMPLIANCE_ENDPOINT_PATH
        },
        timeout=5
    )
    resp.raise_for_status()
    data = resp.json()
    actual = data.get("count", 0)
    assert actual == n, \
        f"Expected {n} calls to compliance service, got {actual}"


@given('compliance service is stubbed to issue attestation on path "{path}"')
def stub_compliance_success_on_path(context, path: str) -> None:
    """WireMock returns 201 with a minimal valid JWT on the given URL path.

    Used by bundle-config override scenarios where the operator repoints the
    bundle's compliancePath at runtime: the test stubs the new path alongside
    the YAML default so call routing can be verified per-path.
    """
    _add_wiremock_stub({
        "request": {
            "method": "POST",
            "urlPathPattern": path
        },
        "response": {
            "status": 201,
            "headers": {"Content-Type": "text/plain"},
            "body": ATTESTATION_JWT
        }
    })


@then('compliance service received {n:d} calls on path "{path}"')
def compliance_service_received_n_calls_on_path(context: ContextType, n: int, path: str) -> None:
    """Query WireMock's __admin/requests/count for a specific URL path pattern."""
    resp = requests.post(
        f"{WIREMOCK_HOST}/__admin/requests/count",
        json={
            "method": "POST",
            "urlPathPattern": path
        },
        timeout=5
    )
    resp.raise_for_status()
    data = resp.json()
    actual = data.get("count", 0)
    assert actual == n, \
        f"Expected {n} POST calls on path '{path}', got {actual}"
