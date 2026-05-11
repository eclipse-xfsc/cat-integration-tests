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
