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
PROFILE_URL = "https://api.prod.whoop.com/v2/user/profile/basic"

DEFAULT_SCOPES = (
    "offline read:profile read:recovery read:cycles read:sleep read:workout read:body_measurement"
)


def default_scopes() -> str:
    return os.getenv("WHOOP_SCOPES", DEFAULT_SCOPES).strip() or DEFAULT_SCOPES


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

    WHOOP returns ``invalid_client`` / "unsupported authentication method" if
    ``client_id``/``client_secret`` are only in the form body. Use **HTTP Basic**
    auth (RFC 6749 §2.3.1): ``Authorization: Basic base64(client_id:client_secret)``,
    with only ``grant_type``, ``code``, and ``redirect_uri`` in the body.
    """
    cid = client_id.strip()
    sec = client_secret.strip()
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": redirect_uri.strip(),
    }
    r = requests.post(
        TOKEN_URL,
        data=data,
        auth=(cid, sec),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    if not r.ok:
        detail = (r.text or "")[:800]
        raise RuntimeError(
            f"HTTP {r.status_code} from token URL: {detail or r.reason}"
        )
    return r.json()


def fetch_profile_user_id(access_token: str) -> int | None:
    """Return WHOOP user_id from /v2/user/profile/basic (requires read:profile)."""
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
