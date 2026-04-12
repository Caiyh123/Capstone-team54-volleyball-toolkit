"""
WHOOP OAuth 2.0 helpers (authorization code + token exchange).

Docs: https://developer.whoop.com/docs/developing/oauth/
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import requests

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
# REST data API base (OpenAPI servers.url); OAuth paths stay under /oauth/ without this prefix.
WHOOP_API_BASE = "https://api.prod.whoop.com/developer"
PROFILE_URL = f"{WHOOP_API_BASE}/v2/user/profile/basic"

DEFAULT_SCOPES = (
    "offline read:profile read:recovery read:cycles read:sleep read:workout read:body_measurement"
)


def default_scopes() -> str:
    return os.getenv("WHOOP_SCOPES", DEFAULT_SCOPES).strip() or DEFAULT_SCOPES


def _clean_oauth_value(s: str) -> str:
    """Strip whitespace and UTF-8 BOM from pasted dashboard / Render values."""
    t = s.strip()
    if t.startswith("\ufeff"):
        t = t[1:].strip()
    return t


def build_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str | None = None,
) -> str:
    """Build GET URL for browser redirect to WHOOP login/consent."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope or default_scopes(),
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_authorization_code(
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """POST authorization code for access + refresh tokens.

    WHOOP registers this app for ``client_secret_post`` only: send
    ``client_id`` and ``client_secret`` in the form body (not HTTP Basic).
    """
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": _clean_oauth_value(code),
        "redirect_uri": _clean_oauth_value(redirect_uri),
        "client_id": _clean_oauth_value(client_id),
        "client_secret": _clean_oauth_value(client_secret),
    }
    r = requests.post(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    if not r.ok:
        detail = (r.text or "")[:800]
        raise RuntimeError(
            f"HTTP {r.status_code} from token URL: {detail or r.reason}"
        )
    return r.json()


def exchange_refresh_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """POST refresh_token for new access_token (client_secret_post)."""
    data: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": _clean_oauth_value(refresh_token),
        "client_id": _clean_oauth_value(client_id),
        "client_secret": _clean_oauth_value(client_secret),
    }
    r = requests.post(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    if not r.ok:
        detail = (r.text or "")[:800]
        raise RuntimeError(
            f"HTTP {r.status_code} from token URL (refresh): {detail or r.reason}"
        )
    return r.json()


def fetch_profile_user_id(access_token: str) -> int | None:
    """Return WHOOP user_id from GET .../developer/v2/user/profile/basic (requires read:profile)."""
    r = requests.get(
        PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    uid = data.get("user_id")
    if uid is None:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None
