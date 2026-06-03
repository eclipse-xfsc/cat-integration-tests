"""
Step definitions for CO-02 validation result storage and retrieval.
"""
import requests
from behave import when, then
from eu.xfsc.bdd.cat.components.fc_server import Server


class ContextType:
    fc_server: Server
    requests_response: requests.Response
    last_asset_id: str


@when("get validations for saved asset")
def get_validations_for_saved_asset(context: ContextType) -> None:
    """GET /assets/{id}/validations for the saved asset ID."""
    assert hasattr(context, "last_asset_id"), \
        "No saved asset id — call 'save asset id from last response' first"
    context.requests_response = context.fc_server.get_asset_validations(context.last_asset_id)


@when('get validations for asset "{asset_id}"')
def get_validations_for_asset(context: ContextType, asset_id: str) -> None:
    """GET /assets/{id}/validations for a specific asset ID."""
    context.requests_response = context.fc_server.get_asset_validations(asset_id)



@when("get validations for saved asset with offset {offset:d} and limit {limit:d}")
def get_validations_for_saved_asset_paginated(
    context: ContextType, offset: int, limit: int
) -> None:
    """GET /assets/{id}/validations with pagination parameters."""
    assert hasattr(context, "last_asset_id"), \
        "No saved asset id — call 'save asset id from last response' first"
    params = {"offset": offset, "limit": limit}
    context.requests_response = context.fc_server.get_asset_validations(
        context.last_asset_id, params=params
    )


@when("get validation result by id {validation_id:d}")
def get_validation_result_by_id(context: ContextType, validation_id: int) -> None:
    """GET /validations/{id}"""
    context.requests_response = context.fc_server.get_validation_result(validation_id)



@then("response has empty list")
def response_has_empty_list(context: ContextType) -> None:
    """Verify response is an empty JSON array."""
    body = context.requests_response.json()
    assert isinstance(body, list), f"Expected list, got {type(body).__name__}: {body}"
    assert len(body) == 0, f"Expected empty list, got {len(body)} items"
