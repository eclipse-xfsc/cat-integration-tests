"""
CAT-specific Keycloak server — uses password grant instead of client_credentials.

The upstream bdd-executor KeycloakServer hardcodes client_credentials grant,
which doesn't work for the Federated Catalogue where we need a user with
specific roles (e.g. Ro-AS-A).
"""
from typing import cast

import requests

from eu.xfsc.bdd.core.defaults import CONNECT_TIMEOUT_IN_SECONDS
from eu.xfsc.bdd.core.server.keycloak import KeycloakServer

from ..env import TEST_PASSWORD, TEST_USER


class CatKeycloakServer(KeycloakServer):
    """KeycloakServer override that uses Resource Owner Password grant."""

    username: str = TEST_USER
    password: str = TEST_PASSWORD

    def fetch_token(self) -> str:
        url = f"{self.host}/realms/{self.realm}/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
            "scope": self.scope,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(
            url=url,
            data=data,
            timeout=CONNECT_TIMEOUT_IN_SECONDS,
        )
        body = response.json()
        if "access_token" not in body:
            raise RuntimeError(
                f"Keycloak token request failed: {response.status_code} — {body}"
            )
        return cast(str, body["access_token"])
