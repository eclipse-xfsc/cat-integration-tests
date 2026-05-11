from behave import given, when, then

from eu.xfsc.bdd.core.server.keycloak import Token
from eu.xfsc.bdd.cat.components.keycloak import CatKeycloakServer

from eu.xfsc.bdd.cat import env


class ContextType:
    keycloak: CatKeycloakServer
    FileToken: Token


@given("CAT Keycloak is up")
def check_cat_keycloak_up(context: ContextType) -> None:
    context.keycloak = CatKeycloakServer(
        host=env.KEYCLOAK_URL,  # type: ignore[arg-type]
        client_secret=env.KEYCLOAK_CLIENT_SECRET,
        client_id=env.KEYCLOAK_CLIENT_ID,
        realm=env.KEYCLOAK_REALM,
        scope=env.KEYCLOAK_SCOPE,
        username=env.TEST_USER,
        password=env.TEST_PASSWORD,
    )
    assert context.keycloak.is_up(), 'Keycloak is not up'


@when("fetch Keycloak token")
def fetch_keycloak_token(context: ContextType) -> None:
    context.keycloak.last_token = context.keycloak.fetch_token()


@then("save Keycloak token")
def save(context: ContextType) -> None:
    context.FileToken.dump(context.keycloak.last_token)


@given("saved Keycloak token")
def load(context: ContextType) -> None:
    context.keycloak.last_token = context.FileToken.load()


@given('Keycloak token for user "{username}" with password "{password}"')
def keycloak_token_for_user(context: ContextType, username: str, password: str) -> None:
    """Fetch a fresh token for a specific Keycloak user (e.g. role-restricted users from realm JSON).

    Overwrites the in-memory token only — the file-cached token is preserved so the next
    scenario reverts to the default user via 'saved Keycloak token'.
    """
    context.keycloak.username = username
    context.keycloak.password = password
    context.keycloak.last_token = context.keycloak.fetch_token()
