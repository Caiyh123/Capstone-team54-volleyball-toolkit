"""
VALD external APIs — OAuth2 client credentials + Bearer requests.

Auth: POST token endpoint with grant_type=client_credentials (see VALD KB).
Regional hosts: Tenants API and Profiles API use different base URLs per region.

Docs:
  https://support.vald.com/hc/en-au/articles/23415335574553-How-to-integrate-with-VALD-APIs
  Tenants: https://support.vald.com/hc/en-au/articles/29360921426585
  Profiles: https://support.vald.com/hc/en-au/articles/29362274413209
  ForceFrame (test summaries): regional Swagger — GET /tests/v2 on api_base_forceframe.
  ForceDecks: api_base_forcedecks — GET /tests, GET /resultdefinitions; team-scoped trials via
  GET /v2019q3/teams/{teamId}/tests/detailed/... (see External ForceDecks Swagger v2019q3).
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests

from integrations import config

# Refresh token this many seconds before expiry to avoid edge races
_TOKEN_SKEW_SEC = 45


class ValdClient:
    """
    Bearer-authenticated client with in-memory token cache.

    Requires in environment:
      VALD_CLIENT_ID, VALD_CLIENT_SECRET
    Optional:
      VALD_OAUTH_TOKEN_URL (default global auth.prd.vald.com)
      VALD_OAUTH_AUDIENCE (default vald-api-external)
      VALD_API_BASE_TENANTS, VALD_API_BASE_PROFILE, VALD_API_BASE_FORCEFRAME, VALD_API_BASE_FORCEDECKS.
    """

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_url: str | None = None,
        audience: str | None = None,
        tenants_base: str | None = None,
        profile_base: str | None = None,
        forceframe_base: str | None = None,
        forcedecks_base: str | None = None,
    ) -> None:
        cfg = config.vald_settings()
        self._client_id = (client_id or cfg["client_id"]).strip()
        self._client_secret = (client_secret or cfg["client_secret"]).strip()
        if not self._client_id or not self._client_secret:
            raise ValueError("VALD_CLIENT_ID and VALD_CLIENT_SECRET must be set")

        self._token_url = (token_url or cfg["oauth_token_url"]).rstrip("/")
        self._audience = (audience or cfg["oauth_audience"]).strip()
        self._tenants_base = (tenants_base or cfg["api_base_tenants"]).rstrip("/")
        self._profile_base = (profile_base or cfg["api_base_profile"]).rstrip("/")
        self._forceframe_base = (forceframe_base or cfg["api_base_forceframe"]).rstrip("/")
        self._forcedecks_base = (forcedecks_base or cfg["api_base_forcedecks"]).rstrip("/")

        self._access_token: str | None = None
        self._access_deadline_monotonic: float = 0.0

    def _fetch_access_token(self) -> str:
        r = requests.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "audience": self._audience,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        if not token or not isinstance(token, str):
            raise ValueError("Token response missing access_token")
        expires_in = int(data.get("expires_in", 3600))
        # monotonic clock avoids DST issues
        self._access_deadline_monotonic = time.monotonic() + max(60, expires_in) - _TOKEN_SKEW_SEC
        self._access_token = token
        return token

    def bearer_token(self) -> str:
        """Return a valid access token, refreshing from cache when needed."""
        if self._access_token and time.monotonic() < self._access_deadline_monotonic:
            return self._access_token
        return self._fetch_access_token()

    def _get_json(
        self,
        base: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.bearer_token()}",
                "Accept": "application/json",
            },
            params=params or {},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()

    def _get_json_allow_empty(
        self,
        base: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Like _get_json but treat 204 No Content as empty payload (no JSON body)."""
        url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.bearer_token()}",
                "Accept": "application/json",
            },
            params=params or {},
            timeout=120,
        )
        if r.status_code == 204:
            return {}
        r.raise_for_status()
        if not (r.content and r.content.strip()):
            return {}
        return r.json()

    def list_tenants(self) -> Any:
        """GET /tenants — tenants visible to this API client."""
        return self._get_json(self._tenants_base, "/tenants")

    def get_tenant(self, tenant_id: str) -> Any:
        """GET /tenants/{tenantId}"""
        tid = tenant_id.strip()
        return self._get_json(self._tenants_base, f"/tenants/{tid}")

    def list_profiles(
        self,
        tenant_id: str,
        *,
        profile_ids: list[str] | None = None,
        group_id: str | None = None,
    ) -> Any:
        """
        GET /profiles — profiles for a tenant.

        Optional filters match External Profiles API query params.
        """
        params: dict[str, Any] = {"tenantId": tenant_id.strip()}
        if profile_ids:
            params["profileIds"] = profile_ids
        if group_id:
            params["groupId"] = group_id
        return self._get_json(self._profile_base, "/profiles", params=params)

    def list_tests_modified_since(
        self,
        tenant_id: str,
        modified_from_utc_iso: str,
        profile_id: str | None = None,
    ) -> Any:
        """
        GET /tests/v2 — ForceFrame test summaries modified on or after ModifiedFromUtc.

        ``modified_from_utc_iso`` should be ISO-8601 UTC (e.g. 2026-05-01T00:00:00Z).
        Optional ``profile_id`` scopes to one athlete; omit for all profiles under the tenant.
        """
        params: dict[str, Any] = {
            "TenantId": tenant_id.strip(),
            "ModifiedFromUtc": modified_from_utc_iso.strip(),
        }
        if profile_id and str(profile_id).strip():
            params["ProfileId"] = str(profile_id).strip()
        return self._get_json_allow_empty(self._forceframe_base, "/tests/v2", params=params)

    def list_forcedecks_tests_modified_since(
        self,
        tenant_id: str,
        modified_from_utc_iso: str,
        profile_id: str | None = None,
    ) -> Any:
        """
        GET /tests on External ForceDecks API — test summaries (TestResponse) modified on or after
        ModifiedFromUtc. Same query shape as ForceFrame /tests/v2 but different product host.
        """
        params: dict[str, Any] = {
            "TenantId": tenant_id.strip(),
            "ModifiedFromUtc": modified_from_utc_iso.strip(),
        }
        if profile_id and str(profile_id).strip():
            params["ProfileId"] = str(profile_id).strip()
        return self._get_json_allow_empty(self._forcedecks_base, "/tests", params=params)

    def list_forcedecks_detailed_tests_date_range(
        self,
        team_id: str,
        date_from_utc_iso: str,
        date_to_utc_iso: str,
    ) -> Any:
        """
        GET /v2019q3/teams/{teamId}/tests/detailed/{dateFrom}/{dateTo}

        Returns an array of DetailedTestDTO (tests with embedded ``trials``). Path segments are
        URL-encoded ISO-8601 datetimes. VALD marks some team paths deprecated but they remain the
        practical way to fetch trial-level results when ``teamId`` is known.
        """
        tid = team_id.strip()
        enc_from = quote(date_from_utc_iso.strip(), safe="")
        enc_to = quote(date_to_utc_iso.strip(), safe="")
        path = f"/v2019q3/teams/{tid}/tests/detailed/{enc_from}/{enc_to}"
        data = self._get_json_allow_empty(self._forcedecks_base, path)
        return data if isinstance(data, list) else []

    def list_forcedecks_result_definitions(self) -> Any:
        """GET /resultdefinitions — metric metadata (resultId, name, unit, …)."""
        return self._get_json_allow_empty(self._forcedecks_base, "/resultdefinitions")
