"""
Additional HTTP status code steps not covered by bdd-executor core.
"""
import requests
from behave import then


class ContextType:
    requests_response: requests.Response


@then("get http 202:Accepted code")
def _202(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 202, \
        (status_code, context.requests_response.content)


@then("get http 400:Bad Request code")
def _400(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 400, \
        (status_code, context.requests_response.content)


@then("get http 401:Unauthorized code")
def _401(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 401, \
        (status_code, context.requests_response.content)


@then("get http 403:Forbidden code")
def _403(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 403, \
        (status_code, context.requests_response.content)


@then("get http 404:Not Found code")
def _404(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 404, \
        (status_code, context.requests_response.content)


# "get http 409:Conflict code" is defined in the bdd-executor core module

@then("get http 422:Unprocessable Entity code")
def _422(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 422, \
        (status_code, context.requests_response.content)


@then("get http 503:Service Unavailable code")
def _503(context: ContextType) -> None:
    status_code = context.requests_response.status_code
    assert status_code == 503, \
        (status_code, context.requests_response.content)
