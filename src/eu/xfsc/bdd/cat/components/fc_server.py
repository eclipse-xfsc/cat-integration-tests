"""
Federated Catalogue Server BDD Wrapper
"""
import json
from typing import Any, Optional
from urllib.parse import quote

import pydantic
import requests

from eu.xfsc.bdd.cat.env import FC_HOST
from eu.xfsc.bdd.core.defaults import CONNECT_TIMEOUT_IN_SECONDS
from eu.xfsc.bdd.core.server.keycloak import BaseServiceKeycloak


class Server(BaseServiceKeycloak):
    """
    Federated Catalogue REST API

    See OpenAPI spec: federated-catalogue/openapi/fc_openapi.yaml
    """
    host: pydantic.HttpUrl = pydantic.HttpUrl(FC_HOST or "http://localhost:8081")

    ASSET_PATH: str = "assets"

    @property
    def health_url(self) -> str:
        return f"{self.host}actuator/health"

    def is_up(self) -> bool:
        try:
            response = requests.get(
                self.health_url,
                timeout=CONNECT_TIMEOUT_IN_SECONDS
            )
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    # -- Assets (credentials + non-RDF) --

    def add_asset(self, payload: str) -> requests.Response:
        """POST /assets (application/json body)"""
        self._update_header(content_type="application/json")
        return self.http.post(
            url=f"{self.host}{self.ASSET_PATH}",
            data=payload.encode("utf-8"),
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def add_asset_with_content_type(self, payload: str, content_type: str) -> requests.Response:
        """POST /assets with specified Content-Type (e.g. application/ld+json, application/vc)"""
        self._update_header(content_type=content_type)
        return self.http.post(
            url=f"{self.host}{self.ASSET_PATH}",
            data=payload.encode("utf-8"),
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def add_asset_multipart(
        self, file_content: bytes, content_type: str, filename: str,
    ) -> requests.Response:
        """POST /assets (multipart/form-data)"""
        self._update_header()
        # Do not set Content-Type header — let requests set the multipart boundary
        self.http.headers.pop("Content-Type", None)
        return self.http.post(
            url=f"{self.host}{self.ASSET_PATH}",
            files={"file": (filename, file_content, content_type)},
            timeout=CONNECT_TIMEOUT_IN_SECONDS,
        )

    def add_asset_raw(self, file_content: bytes, content_type: str) -> requests.Response:
        """POST /assets (raw binary with specified content-type)"""
        self._update_header(content_type=content_type)
        return self.http.post(
            url=f"{self.host}{self.ASSET_PATH}",
            data=file_content,
            timeout=CONNECT_TIMEOUT_IN_SECONDS,
        )

    def get_assets(self, params: Optional[dict[str, Any]] = None) -> requests.Response:
        """GET /assets"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}{self.ASSET_PATH}",
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def get_asset(self, asset_id: str, version: Optional[int] = None) -> requests.Response:
        """GET /assets/{id}[?version=X]"""
        self._update_header()
        params = {"version": version} if version is not None else None
        return self.http.get(
            url=f"{self.host}{self.ASSET_PATH}/{quote(asset_id, safe='')}",
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def update_asset(self, asset_id: str, payload: str, change_comment: Optional[str] = None) -> requests.Response:
        """PUT /assets/{id}[?changeComment=...]"""
        self._update_header(content_type="application/json")
        params = {"changeComment": change_comment} if change_comment is not None else None
        return self.http.put(
            url=f"{self.host}{self.ASSET_PATH}/{quote(asset_id, safe='')}",
            data=payload.encode("utf-8"),
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def get_asset_versions(self, asset_id: str) -> requests.Response:
        """GET /assets/{id}/versions"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}{self.ASSET_PATH}/{quote(asset_id, safe='')}/versions",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def delete_asset(self, asset_hash: str) -> requests.Response:
        """DELETE /assets/{asset_hash}"""
        self._update_header()
        return self.http.delete(
            url=f"{self.host}{self.ASSET_PATH}/{asset_hash}",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def revoke_asset(self, asset_hash: str) -> requests.Response:
        """POST /assets/{asset_hash}/revoke"""
        self._update_header()
        return self.http.post(
            url=f"{self.host}{self.ASSET_PATH}/{asset_hash}/revoke",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Verification --

    def verify(self, payload: str, params: Optional[dict[str, Any]] = None) -> requests.Response:
        """POST /verification"""
        self._update_header(content_type="application/json")
        return self.http.post(
            url=f"{self.host}verification",
            data=payload.encode("utf-8"),
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Query --

    def query(self, statement: str, query_language: str = "opencypher") -> requests.Response:
        """POST /query — raw query text with language-specific Content-Type."""
        content_type = f"application/{query_language}-query"
        self._update_header(content_type=content_type)
        return self.http.post(
            url=f"{self.host}query",
            data=statement.encode("utf-8"),
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Schemas --

    def get_schemas(self, params: Optional[dict[str, Any]] = None) -> requests.Response:
        """GET /schemas"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}schemas",
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def add_schema(self, payload: str, content_type: str = "application/json") -> requests.Response:
        """POST /schemas"""
        self._update_header(content_type=content_type)
        return self.http.post(
            url=f"{self.host}schemas",
            data=payload.encode("utf-8"),
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def get_schema(self, schema_id: str, version: Optional[int] = None) -> requests.Response:
        """GET /schemas/{schemaId}[?version=X]"""
        self._update_header()
        params = {"version": version} if version is not None else None
        return self.http.get(
            url=f"{self.host}schemas/{schema_id}",
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def update_schema(self, schema_id: str, payload: str, content_type: str = "application/json") -> requests.Response:
        """PUT /schemas/{schemaId}"""
        self._update_header(content_type=content_type)
        return self.http.put(
            url=f"{self.host}schemas/{schema_id}",
            data=payload.encode("utf-8"),
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def delete_schema(self, schema_id: str) -> requests.Response:
        """DELETE /schemas/{schemaId}"""
        self._update_header()
        return self.http.delete(
            url=f"{self.host}schemas/{schema_id}",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Participants --

    def get_participants(self, params: Optional[dict[str, Any]] = None) -> requests.Response:
        """GET /participants"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}participants",
            params=params,
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def get_participant(self, participant_id: str) -> requests.Response:
        """GET /participants/{participantId}"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}participants/{participant_id}",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Session --

    def get_session(self) -> requests.Response:
        """GET /session"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}session",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    # -- Admin API --

    def get_admin_stats(self) -> requests.Response:
        """GET /admin/stats"""
        self._update_header()
        return self.http.get(
            url=f"{self.host}admin/stats",
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def set_schema_module_enabled(self, module_type: str, enabled: bool) -> requests.Response:
        """PUT /admin/schema-validation/modules/{type}?enabled=<bool>"""
        self._update_header(content_type=None)
        return self.http.put(
            url=f"{self.host}admin/schema-validation/modules/{module_type}",
            params={"enabled": str(enabled).lower()},
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )

    def set_trust_framework_enabled(self, framework_id: str, enabled: bool) -> requests.Response:
        """PUT /admin/trust-frameworks/{id}/enabled?enabled=<bool>"""
        self._update_header(content_type=None)
        return self.http.put(
            url=f"{self.host}admin/trust-frameworks/{framework_id}/enabled",
            params={"enabled": str(enabled).lower()},
            timeout=CONNECT_TIMEOUT_IN_SECONDS
        )
