"""
Step definitions for Graph Database admin endpoints.

Covers status, switch, and rebuild trigger/poll. Restart-required scenarios (cold-boot
fallback, persistence across `docker restart fc-server`) and reachability rejection
(requires stopping a backend container from inside the test) are out of scope here —
keep those manual or move them to a docker-aware suite.
"""
import time
from pathlib import Path

import requests
from behave import given, then, when

from eu.xfsc.bdd.cat.components.fc_server import Server


VALID_BACKENDS = {"NEO4J", "FUSEKI", "NONE"}
REBUILD_POLL_INTERVAL_SECONDS = 2
REBUILD_POLL_MAX_ATTEMPTS = 30  # ~60s max
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class ContextType:
    fc_server: Server
    requests_response: requests.Response
    initial_backend: str
    baseline_claim_count: int


# ---------------------------------------------------------------------------
# Setup / teardown helpers
# ---------------------------------------------------------------------------

@given("the active graph backend is {backend}")
def ensure_backend_active(context: ContextType, backend: str) -> None:
    """Switch to the requested backend if not already there. Records the prior
    backend in context.initial_backend so a teardown step can restore it."""
    assert backend in VALID_BACKENDS, f"Unknown backend: {backend}"
    status = context.fc_server.get_graph_database_status().json()
    context.initial_backend = status["activeBackend"]
    if status["activeBackend"] == backend:
        return
    resp = context.fc_server.switch_graph_database(backend)
    assert resp.status_code == 200, \
        f"Setup switch to {backend} failed: {resp.status_code} {resp.text}"


@then("the original graph backend is restored")
def restore_original_backend(context: ContextType) -> None:
    if not hasattr(context, "initial_backend"):
        return
    current = context.fc_server.get_graph_database_status().json()["activeBackend"]
    if current == context.initial_backend:
        return
    resp = context.fc_server.switch_graph_database(context.initial_backend)
    assert resp.status_code == 200, \
        f"Teardown restore to {context.initial_backend} failed: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Switch endpoint
# ---------------------------------------------------------------------------

@when('switch graph backend to "{backend}"')
def switch_backend(context: ContextType, backend: str) -> None:
    context.requests_response = context.fc_server.switch_graph_database(backend)


@then('active graph backend is "{backend}"')
def assert_active_backend(context: ContextType, backend: str) -> None:
    resp = context.fc_server.get_graph_database_status()
    assert resp.status_code == 200, f"GET status failed: {resp.status_code}"
    actual = resp.json().get("activeBackend")
    assert actual == backend, f"Expected activeBackend={backend}, got {actual}"


@then("switch response message mentions the target backend")
def assert_switch_message_present(context: ContextType) -> None:
    body = context.requests_response.json()
    assert "message" in body, f"Response missing 'message' field: {body}"
    assert body["message"], "Response message is empty"


@then("response has no restartRequired field")
def assert_no_restart_required(context: ContextType) -> None:
    body = context.requests_response.json()
    assert "restartRequired" not in body, \
        f"Live switch response must not carry restartRequired; got {body}"


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@when("request graph database status")
def request_status(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_graph_database_status()


@then("graph database status has live-switch shape")
def assert_status_shape(context: ContextType) -> None:
    """Asserts the live-switch status shape: required fields present, deprecated fields gone."""
    body = context.requests_response.json()
    required = {"activeBackend", "connected", "claimCount", "version",
                "rebuildNeeded", "rdfAssetCount"}
    missing = required - body.keys()
    assert not missing, f"Status missing fields: {missing}. Got: {list(body.keys())}"
    forbidden = {"preferredBackend", "restartRequired"}
    leaked = forbidden & body.keys()
    assert not leaked, \
        f"Status must not carry deprecated fields {leaked}; got body: {body}"


# ---------------------------------------------------------------------------
# Rebuild endpoint
# ---------------------------------------------------------------------------

@when("trigger graph rebuild")
def trigger_rebuild(context: ContextType) -> None:
    context.requests_response = context.fc_server.trigger_graph_rebuild()


@then("graph rebuild completes within timeout")
def poll_rebuild_until_done(context: ContextType) -> None:
    """Polls rebuild status until running=false; asserts complete=true, failed=false,
    and errors=0. The errors check catches per-asset extraction failures (e.g. a JWT
    asset that the rebuild path could not decode) that otherwise slip past failed=false."""
    for _ in range(REBUILD_POLL_MAX_ATTEMPTS):
        resp = context.fc_server.get_graph_rebuild_status()
        assert resp.status_code == 200, f"Poll failed: {resp.status_code}"
        body = resp.json()
        if not body.get("running", True):
            assert body.get("complete") is True, \
                f"Rebuild stopped but not complete: {body}"
            assert body.get("failed") is False, \
                f"Rebuild reported failed=true: {body}"
            assert body.get("errors", 0) == 0, \
                f"Rebuild reported per-asset extraction errors: {body}"
            return
        time.sleep(REBUILD_POLL_INTERVAL_SECONDS)
    raise AssertionError(
        f"Rebuild did not complete within "
        f"{REBUILD_POLL_INTERVAL_SECONDS * REBUILD_POLL_MAX_ATTEMPTS}s"
    )


# ---------------------------------------------------------------------------
# Claim-growth helpers (rebuild re-indexes stored assets into the active graph)
# ---------------------------------------------------------------------------

@given('a credential from fixture "{fixture_path}" is uploaded with content-type "{content_type}"')
def upload_credential_fixture(context: ContextType, fixture_path: str, content_type: str) -> None:
    """Uploads a fixture credential so the next rebuild has non-trivial work to do."""
    payload = (FIXTURES_DIR / fixture_path).read_text()
    resp = context.fc_server.add_asset_with_content_type(payload, content_type)
    assert resp.status_code in (200, 201), \
        f"Fixture upload failed: {resp.status_code} {resp.text}"
    context.requests_response = resp


@given("the current graph claim count is recorded")
def record_claim_count(context: ContextType) -> None:
    body = context.fc_server.get_graph_database_status().json()
    context.baseline_claim_count = body.get("claimCount", 0)


@then("the graph claim count grew beyond the recorded baseline")
def assert_claim_count_grew(context: ContextType) -> None:
    """A successful rebuild of a JWT-secured credential must re-index its claims, so the
    active-graph claim count exceeds the pre-upload baseline. Before CAT-FR-GD-01 the JWT
    body reached the extractors raw and yielded zero claims, so the count did not grow."""
    body = context.fc_server.get_graph_database_status().json()
    current = body.get("claimCount", 0)
    assert current > context.baseline_claim_count, \
        f"Expected claim count to grow beyond {context.baseline_claim_count}, got {current}"


# ---------------------------------------------------------------------------
# Error-case assertions
# ---------------------------------------------------------------------------

@then('response message lists valid backends')
def assert_message_lists_valid_backends(context: ContextType) -> None:
    """For invalid-backend rejection: error message must list the accepted values
    so the operator can self-correct."""
    body = context.requests_response.json()
    msg = body.get("message", "")
    for backend in VALID_BACKENDS:
        assert backend in msg, \
            f"Expected '{backend}' in error message; got: {msg}"
