"""Persist WHOOP OAuth tokens to Postgres (shared by Auth Bridge and ETL)."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import Json

UPSERT_SQL = """
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


def upsert_whoop_token_row(
    *,
    state_label: str | None,
    whoop_user_id: str,
    refresh_token: str | None,
    access_token: str | None,
    expires_at: datetime | None,
    scope: str | None,
    raw: dict[str, Any],
    needs_reconnect: bool,
    database_url: str | None = None,
) -> None:
    db = (database_url or os.getenv("DATABASE_URL", "")).strip()
    if not db:
        raise RuntimeError("DATABASE_URL is not set; cannot store WHOOP tokens.")

    conn = psycopg2.connect(db)
    try:
        cur = conn.cursor()
        cur.execute(
            UPSERT_SQL,
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
