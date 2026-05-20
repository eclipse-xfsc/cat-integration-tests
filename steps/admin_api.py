"""
Step definitions for Admin API scenarios (CAT-FR-AU-01).

Covers: schema validation module toggles, trust framework enabled toggle, and admin stats.
"""
import requests
from behave import given, then, when

from eu.xfsc.bdd.cat.components.fc_server import Server

GAIAX_TRUST_FRAMEWORK_ID = "gaia-x"
GAIAX_BUNDLE_ID = "gaia-x-2511"
MOCK_TRUST_FRAMEWORK_ID = "mock"
SHACL_MODULE_TYPE = "SHACL"
JSON_SCHEMA_MODULE_TYPE = "JSON_SCHEMA"
XML_SCHEMA_MODULE_TYPE = "XML_SCHEMA"

ROLE_SERVICE_OFFERING = "ServiceOffering"
ROLE_PARTICIPANT = "Participant"
ROLE_RESOURCE = "Resource"


class ContextType:
    fc_server: Server
    requests_response: requests.Response


# ---------------------------------------------------------------------------
# Schema Validation Module Toggle
# ---------------------------------------------------------------------------

@given("SHACL schema module is disabled")
def disable_shacl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(SHACL_MODULE_TYPE, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable SHACL module: {resp.status_code} {resp.text}"


@given("SHACL schema module is enabled")
def enable_shacl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(SHACL_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable SHACL module: {resp.status_code} {resp.text}"


@then("SHACL schema module is re-enabled")
def reenable_shacl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(SHACL_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable SHACL module: {resp.status_code} {resp.text}"


@given("JSON Schema module is disabled")
def disable_json_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(JSON_SCHEMA_MODULE_TYPE, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable JSON_SCHEMA module: {resp.status_code} {resp.text}"


@then("JSON Schema module is re-enabled")
def reenable_json_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(JSON_SCHEMA_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable JSON_SCHEMA module: {resp.status_code} {resp.text}"


@given("XML Schema module is disabled")
def disable_xml_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(XML_SCHEMA_MODULE_TYPE, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable XML_SCHEMA module: {resp.status_code} {resp.text}"


@then("XML Schema module is re-enabled")
def reenable_xml_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(XML_SCHEMA_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable XML_SCHEMA module: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Trust Framework Toggle
# ---------------------------------------------------------------------------

@given("Gaia-X trust framework is disabled")
def disable_gaiax_trust_framework(context: ContextType) -> None:
    resp = context.fc_server.set_trust_framework_enabled(GAIAX_TRUST_FRAMEWORK_ID, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable Gaia-X trust framework: {resp.status_code} {resp.text}"


@given("Gaia-X trust framework is enabled")
def enable_gaiax_trust_framework(context: ContextType) -> None:
    resp = context.fc_server.set_trust_framework_enabled(GAIAX_TRUST_FRAMEWORK_ID, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable Gaia-X trust framework: {resp.status_code} {resp.text}"


@then("Gaia-X trust framework is disabled")
def disable_gaiax_trust_framework_cleanup(context: ContextType) -> None:
    resp = context.fc_server.set_trust_framework_enabled(GAIAX_TRUST_FRAMEWORK_ID, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable Gaia-X trust framework: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Mock Trust Framework Toggle
# ---------------------------------------------------------------------------

@given("mock trust framework is enabled")
@then("mock trust framework is re-enabled")
def enable_mock_trust_framework(context: ContextType) -> None:
    resp = context.fc_server.set_trust_framework_enabled(MOCK_TRUST_FRAMEWORK_ID, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable mock trust framework: {resp.status_code} {resp.text}"


@given("mock trust framework is disabled")
def disable_mock_trust_framework(context: ContextType) -> None:
    resp = context.fc_server.set_trust_framework_enabled(MOCK_TRUST_FRAMEWORK_ID, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable mock trust framework: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Admin Stats
# ---------------------------------------------------------------------------

@when("request admin stats")
def request_admin_stats(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_admin_stats()


@then("response has admin stats fields")
def response_has_admin_stats_fields(context: ContextType) -> None:
    body = context.requests_response.json()
    expected_fields = {
        "totalAssets", "activeAssets", "activeTrustFrameworks",
        "totalUsers", "totalSchemas", "totalParticipants",
        "graphClaimCount", "graphBackend",
    }
    missing = expected_fields - body.keys()
    assert not missing, f"Admin stats response missing fields: {missing}. Got: {list(body.keys())}"


# ---------------------------------------------------------------------------
# Trust Framework Role Toggle (CAT-FR-AU-01 Story 048)
# ---------------------------------------------------------------------------

@given('role {role_name} of bundle {bundle_id} is disabled')
def disable_trust_framework_role(context: ContextType, role_name: str, bundle_id: str) -> None:
    resp = context.fc_server.set_trust_framework_role_enabled(bundle_id, role_name, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable role {bundle_id}/{role_name}: {resp.status_code} {resp.text}"


@then('role {role_name} of bundle {bundle_id} is re-enabled')
def reenable_trust_framework_role(context: ContextType, role_name: str, bundle_id: str) -> None:
    resp = context.fc_server.set_trust_framework_role_enabled(bundle_id, role_name, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable role {bundle_id}/{role_name}: {resp.status_code} {resp.text}"


@when("request admin trust frameworks")
def request_admin_trust_frameworks(context: ContextType) -> None:
    """GET /admin/trust-frameworks"""
    context.requests_response = context.fc_server.get_admin_trust_frameworks()


@then('admin trust frameworks response includes bundle "{bundle_id}" with role "{role_name}" enabled')
def admin_trust_frameworks_bundle_role_enabled(
    context: ContextType, bundle_id: str, role_name: str
) -> None:
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    # Find any family entry that contains a bundle with the given id
    bundle = None
    for family in body:
        for b in family.get("bundles", []):
            if b.get("id") == bundle_id:
                bundle = b
                break
        if bundle:
            break
    assert bundle is not None, \
        f"Bundle '{bundle_id}' not found in admin trust-frameworks response: {body}"
    roles = bundle.get("roles", {})
    assert role_name in roles, \
        f"Role '{role_name}' not found in bundle '{bundle_id}' roles: {roles}"
    assert roles[role_name] is True, \
        f"Expected role '{bundle_id}/{role_name}' to be enabled (true), got: {roles[role_name]}"
