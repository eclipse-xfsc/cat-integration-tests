"""
Step definitions for Admin API scenarios (CAT-FR-AU-01).

Covers: schema validation module toggles, trust framework enabled toggle, and admin stats.
"""
import requests
from behave import given, then, when

from eu.xfsc.bdd.cat.components.fc_server import Server

GAIAX_TRUST_FRAMEWORK_ID = "gaia-x"
SHACL_MODULE_TYPE = "SHACL"
JSON_SCHEMA_MODULE_TYPE = "JSON_SCHEMA"
XML_SCHEMA_MODULE_TYPE = "XML_SCHEMA"
OWL_MODULE_TYPE = "OWL"


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


@given("JSON Schema module is enabled")
def enable_json_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(JSON_SCHEMA_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable JSON_SCHEMA module: {resp.status_code} {resp.text}"


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


@given("XML Schema module is enabled")
def enable_xml_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(XML_SCHEMA_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable XML_SCHEMA module: {resp.status_code} {resp.text}"


@then("XML Schema module is re-enabled")
def reenable_xml_schema_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(XML_SCHEMA_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable XML_SCHEMA module: {resp.status_code} {resp.text}"


@given("OWL schema module is disabled")
def disable_owl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(OWL_MODULE_TYPE, enabled=False)
    assert resp.status_code == 200, \
        f"Failed to disable OWL module: {resp.status_code} {resp.text}"


@given("OWL schema module is enabled")
def enable_owl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(OWL_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to enable OWL module: {resp.status_code} {resp.text}"


@then("OWL schema module is re-enabled")
def reenable_owl_module(context: ContextType) -> None:
    resp = context.fc_server.set_schema_module_enabled(OWL_MODULE_TYPE, enabled=True)
    assert resp.status_code == 200, \
        f"Failed to re-enable OWL module: {resp.status_code} {resp.text}"


@when('set schema module "{module_type}" to enabled')
def set_schema_module_enabled_generic(context: ContextType, module_type: str) -> None:
    """Generic PUT for negative cases (e.g. invalid module type names)."""
    context.requests_response = context.fc_server.set_schema_module_enabled(
        module_type, enabled=True
    )


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
# Ontology Impact
# ---------------------------------------------------------------------------

@when("request ontology impact list")
def request_ontology_impact(context: ContextType) -> None:
    context.requests_response = context.fc_server.get_ontology_impact()


@then("response items is an array")
def response_items_is_array(context: ContextType) -> None:
    body = context.requests_response.json()
    assert isinstance(body.get("items"), list), \
        f"Expected 'items' to be a list, got: {type(body.get('items'))}. Body: {body}"


@then("response items has at least {count:d} entry")
@then("response items has at least {count:d} entries")
def response_items_has_at_least(context: ContextType, count: int) -> None:
    body = context.requests_response.json()
    items = body.get("items", [])
    assert len(items) >= count, \
        f"Expected at least {count} items, got {len(items)}. Body: {body}"


@then('response items contributions contain "{role_name}"')
def response_items_contributions_contain(context: ContextType, role_name: str) -> None:
    body = context.requests_response.json()
    items = body.get("items", [])
    matching = [it for it in items if role_name in (it.get("contributions") or {})]
    assert matching, \
        f"No item has contribution for role '{role_name}'. Items: {items}"


