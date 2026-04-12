"""
WHOOP OAuth Auth Bridge (FastAPI).

Deploy to HTTPS (e.g. Render). Register WHOOP_REDIRECT_URI exactly, e.g.
https://<service>.onrender.com/callback

Local:  uvicorn backend.app:app --reload --port 8000
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from psycopg2.extras import Json

from integrations.whoop.oauth import (
    build_authorize_url,
    exchange_authorization_code,
    fetch_profile_user_id,
)

load_dotenv()

app = FastAPI(title="Volleyball toolkit — WHOOP Auth Bridge", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    """Avoid bare 404 when someone opens the service URL in a browser."""
    return {
        "service": "WHOOP Auth Bridge",
        "health": "/health",
        "whoop_start": "/whoop/start?state=<8+ chars>",
        "oauth_check": "/whoop/oauth-check",
    }


@app.get("/whoop/oauth-check")
def whoop_oauth_check() -> dict[str, Any]:
    """Exact redirect_uri + sanity checks for WHOOP env (no secrets exposed)."""
    cid = os.getenv("WHOOP_CLIENT_ID", "").strip()
    sec = os.getenv("WHOOP_CLIENT_SECRET", "").strip()
    redir = os.getenv("WHOOP_REDIRECT_URI", "").strip()
    if not cid or not redir:
        raise HTTPException(
            status_code=503,
            detail="WHOOP_CLIENT_ID or WHOOP_REDIRECT_URI missing.",
        )
    return {
        "redirect_uri": redir,
        "client_id_prefix": cid[:12] + ("…" if len(cid) > 12 else ""),
        "client_id_length": len(cid),
        "client_secret_configured": bool(sec),
        "client_secret_length": len(sec),
        "hint": "invalid_client = wrong client_id/secret for this app, or secret empty in Render. Re-copy from WHOOP Dashboard (same app as redirect URI).",
    }


def _req_whoop() -> tuple[str, str, str]:
    cid = os.getenv("WHOOP_CLIENT_ID", "").strip()
    sec = os.getenv("WHOOP_CLIENT_SECRET", "").strip()
    redir = os.getenv("WHOOP_REDIRECT_URI", "").strip()
    if not cid or not sec or not redir:
        raise HTTPException(
            status_code=503,
            detail="Missing WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, or WHOOP_REDIRECT_URI in environment.",
        )
    return cid, sec, redir


def _upsert_token_row(
    *,
    state_label: str | None,
    whoop_user_id: str,
    refresh_token: str | None,
    access_token: str | None,
    expires_at: datetime | None,
    scope: str | None,
    raw: dict[str, Any],
    needs_reconnect: bool,
) -> None:
    db = os.getenv("DATABASE_URL", "").strip()
    if not db:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not set; cannot store tokens.",
        )

    sql = """
    INSERT INTO public.whoop_oauth_token (
        state_label, whoop_user_id, refresh_token, access_token, expires_at,
        scope, raw_token_response, updated_at, needs_reconnect
    ) VALUES (
        %(state_label)s, %(whoop_user_id)s, %(refresh_token)s, %(access_token)s, %(expires_at)s,
        %(scope)s, %(raw_token_response)s, NOW(), %(needs_reconnect)s
    )
    ON CONFLICT (whoop_user_id) DO UPDATE SET
        state_label = COALESCE(EXCLUDED.state_label, public.whoop_oauth_token.state_label),
        refresh_token = EXCLUDED.refresh_token,
        access_token = EXCLUDED.access_token,
        expires_at = EXCLUDED.expires_at,
        scope = EXCLUDED.scope,
        raw_token_response = EXCLUDED.raw_token_response,
        updated_at = NOW(),
        needs_reconnect = EXCLUDED.needs_reconnect
    """
    conn = psycopg2.connect(db)
    try:
        cur = conn.cursor()
        cur.execute(
            sql,
            {
                "state_label": state_label,
                "whoop_user_id": whoop_user_id,
                "refresh_token": refresh_token,
                "access_token": access_token,
                "expires_at": expires_at,
                "scope": scope,
                "raw_token_response": Json(raw),
                "needs_reconnect": needs_reconnect,
            },
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.head("/health")
def health_head() -> Response:
    """Some uptime tools use HEAD; default GET-only would return 405."""
    return Response(status_code=200)


@app.get("/whoop/start")
def whoop_start(
    state: str = Query(
        ...,
        min_length=8,
        description="Opaque label (e.g. internal athlete id). WHOOP requires state >= 8 characters.",
    ),
) -> RedirectResponse:
    """Redirect browser to WHOOP login/consent."""
    client_id, _, redirect_uri = _req_whoop()
    url = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(url=url, status_code=302)


@app.get("/callback")
def whoop_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    """WHOOP redirects here after consent. Must match WHOOP_REDIRECT_URI path + host."""
    if error:
        msg = error_description or error
        return HTMLResponse(
            f"<html><body><p>Authorization failed: {msg}</p></body></html>",
            status_code=400,
        )
    if not code:
        raise HTTPException(400, "Missing authorization code.")

    client_id, client_secret, redirect_uri = _req_whoop()

    try:
        token_json = exchange_authorization_code(
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as e:
        return HTMLResponse(
            f"<html><body><p>Token exchange failed: {e}</p></body></html>",
            status_code=502,
        )

    access_token = token_json.get("access_token")
    if not access_token or not isinstance(access_token, str):
        return HTMLResponse(
            "<html><body><p>Token response had no access_token.</p></body></html>",
            status_code=502,
        )

    try:
        uid = fetch_profile_user_id(access_token)
    except Exception as e:
        return HTMLResponse(
            f"<html><body><p>Profile fetch failed (check read:profile scope): {e}</p></body></html>",
            status_code=502,
        )

    if uid is None:
        return HTMLResponse(
            "<html><body><p>Could not resolve WHOOP user_id from profile.</p></body></html>",
            status_code=502,
        )

    whoop_user_id = str(uid)
    refresh_token = token_json.get("refresh_token")
    if not refresh_token:
        # ETL needs offline scope for long-lived refresh
        needs_reconnect = True
    else:
        needs_reconnect = False

    expires_in = token_json.get("expires_in")
    expires_at: datetime | None = None
    if expires_in is not None:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            pass

    scope = token_json.get("scope")
    if isinstance(scope, str):
        scope_str = scope
    else:
        scope_str = None

    try:
        _upsert_token_row(
            state_label=state,
            whoop_user_id=whoop_user_id,
            refresh_token=str(refresh_token) if refresh_token else None,
            access_token=access_token,
            expires_at=expires_at,
            scope=scope_str,
            raw=token_json,
            needs_reconnect=needs_reconnect,
        )
    except HTTPException:
        raise
    except Exception as e:
        return HTMLResponse(
            f"<html><body><p>Database error: {e}</p></body></html>",
            status_code=502,
        )

    extra = ""
    if needs_reconnect:
        extra = (
            "<p><strong>Warning:</strong> No refresh token was returned. "
            "Request the <code>offline</code> scope and reconnect.</p>"
        )

    return HTMLResponse(
        "<html><body>"
        "<p>Success. WHOOP is linked for this account. You can close this tab.</p>"
        f"{extra}"
        "</body></html>",
        status_code=200,
    )
