# noinspection PyUnresolvedReferences
import urllib.parse

from eu.xfsc.bdd.core import environment
# noinspection PyUnresolvedReferences
from eu.xfsc.bdd.core.steps import *
from eu.xfsc.bdd.core.server.keycloak import Token
from pathlib import Path


def before_all(context) -> None:
    environment.before_all(context)

    context.FileToken = Token(Path(__file__).parent / ".tmp")


def before_scenario(context, scenario) -> None:
    """Reset multi-asset tracking to avoid cross-scenario leakage."""
    if hasattr(context, "last_asset_ids"):
        del context.last_asset_ids


def after_scenario(context, scenario) -> None:
    """Always clean up uploaded schemas to prevent cross-scenario leakage when a scenario fails."""
    try:
        schema_ids = list(context._uploaded_schema_ids)
    except (AttributeError, KeyError):
        schema_ids = []
    for schema_id in schema_ids:
        try:
            encoded = urllib.parse.quote(schema_id, safe="")
            context.fc_server.delete_schema(encoded)
        except Exception:  # noqa: BLE001
            pass
    try:
        context._uploaded_schema_ids = []
    except (AttributeError, KeyError):
        pass

    # Restore any role-toggle states that were disabled during the scenario.
    # This runs unconditionally so that a failed assertion cannot leave a role disabled
    # and poison subsequent scenarios (@domain.admin role-toggle tests).
    try:
        disabled_roles = list(context.disabled_roles)
    except AttributeError:
        disabled_roles = []
    for bundle_id, role_name in disabled_roles:
        try:
            context.fc_server.set_trust_framework_role_enabled(bundle_id, role_name, enabled=True)
        except Exception:  # noqa: BLE001
            pass
    try:
        context.disabled_roles = []
    except AttributeError:
        pass

    # Restore any schema-validation modules that were disabled during the scenario.
    # Same rationale as above — a mid-scenario failure must not leak a disabled module
    # into subsequent scenarios (recurring: SHACL/JSON_SCHEMA/XML_SCHEMA/OWL toggles).
    try:
        disabled_modules = list(context.disabled_schema_modules)
    except AttributeError:
        disabled_modules = []
    for module_type in disabled_modules:
        try:
            context.fc_server.set_schema_module_enabled(module_type, enabled=True)
        except Exception:  # noqa: BLE001
            pass
    try:
        context.disabled_schema_modules = []
    except AttributeError:
        pass

    # Clear any per-bundle config overrides applied during the scenario so a
    # mid-scenario failure cannot leave a bundle pointing at a stale compliance
    # endpoint and poison subsequent scenarios (CAT-FR-CO-03 bundle-config tests).
    try:
        overridden_bundles = list(context.overridden_bundles)
    except AttributeError:
        overridden_bundles = []
    for bundle_id in overridden_bundles:
        try:
            context.fc_server.delete_trust_framework_bundle_config(bundle_id)
        except Exception:  # noqa: BLE001
            pass
    try:
        context.overridden_bundles = []
    except AttributeError:
        pass
