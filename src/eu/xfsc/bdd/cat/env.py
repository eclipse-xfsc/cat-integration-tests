"""
Keep all OS env used.
"""
import os

from .defaults import PREFIX

# pylint: disable=line-too-long
# :start: Federated Catalogue
FC_HOST = os.getenv(PREFIX + "_FC_HOST")
# :end: Federated Catalogue

# :start: Keycloak
KEYCLOAK_URL = os.getenv(PREFIX + "_KEYCLOAK_URL") or ""
KEYCLOAK_REALM = os.getenv(PREFIX + "_KEYCLOAK_REALM") or ""
KEYCLOAK_CLIENT_ID = os.getenv(PREFIX + "_KEYCLOAK_CLIENT_ID") or ""
KEYCLOAK_CLIENT_SECRET = os.getenv(PREFIX + "_KEYCLOAK_CLIENT_SECRET") or ""
KEYCLOAK_SCOPE = os.getenv(PREFIX + "_KEYCLOAK_SCOPE") or ""
# :end: Keycloak

# :start: Test User
TEST_USER = os.getenv(PREFIX + "_TEST_USER") or ""
TEST_PASSWORD = os.getenv(PREFIX + "_TEST_PASSWORD") or ""
# :end: Test User

# pylint: enable=line-too-long
