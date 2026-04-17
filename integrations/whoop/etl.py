"""WHOOP to Supabase staging: refresh tokens, paginated pulls, append-only raw inserts."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_batch

from integrations.whoop.api import iter_collection_records
from integrations.whoop.oauth import (
    _clean_oauth_value,
    exchange_refresh_token,
    WHOOP_API_BASE,
)
from integrations.whoop.token_store import upsert_whoop_token_row


@dataclass
class TokenRow:
    whoop_user_id: str
    refresh_token: str | None
    access_token: str | None
    expires_at: datetime | None
    state_label: str | None


def _parse_iso_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str) and v.strip():
        try:
            # fromisoformat handles ...Z in Python 3.11+
            s = v.strip().replace("Z", "+00:00")
            d = datetime.fromisoformat(s)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def expires_at_from_token_json(token_json: dict[str, Any]) -> datetime | None:
    expires_in = token_json.get("expires_in")
    if expires_in is None:
        return None
    try:
        return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
    except (TypeError, ValueError):
        return None


def load_token_rows(
    database_url: str,
    *,
    whoop_user_id: str | None = None,
    allowed_state_labels: set[str] | None = None,
) -> list[TokenRow]:
    conn = psycopg2.connect(database_url)
    try:
        cur = conn.cursor()
        if whoop_user_id:
            cur.execute(
                """
                SELECT whoop_user_id, refresh_token, access_token, expires_at, state_label
                FROM public.whoop_oauth_token
                WHERE needs_reconnect = FALSE
                  AND refresh_token IS NOT NULL
                  AND whoop_user_id = %s
                """,
                (whoop_user_id.strip(),),
            )
        else:
            cur.execute(
                """
                SELECT whoop_user_id, refresh_token, access_token, expires_at, state_label
                FROM public.whoop_oauth_token
                WHERE needs_reconnect = FALSE
                  AND refresh_token IS NOT NULL
                """
            )
        rows: list[TokenRow] = []
        for r in cur.fetchall():
            rows.append(
                TokenRow(
                    whoop_user_id=str(r[0]),
                    refresh_token=r[1],
                    access_token=r[2],
                    expires_at=_parse_iso_dt(r[3]),
                    state_label=r[4],
                )
            )
        if allowed_state_labels is not None:
            allow = {s.strip() for s in allowed_state_labels if s and str(s).strip()}
            rows = [
                x
                for x in rows
                if x.state_label and str(x.state_label).strip() in allow
            ]
        cur.close()
        return rows
    finally:
        conn.close()


def _access_token_needs_refresh(
    expires_at: datetime | None,
    *,
    skew_seconds: int = 300,
) -> bool:
    if not expires_at:
        return True
    now = datetime.now(timezone.utc)
    return expires_at <= now + timedelta(seconds=skew_seconds)


def refresh_and_persist_tokens(
    row: TokenRow,
    *,
    client_id: str,
    client_secret: str,
    database_url: str,
) -> str:
    """Return a valid access token, refreshing and upserting the row if needed."""
    if not row.refresh_token:
        raise RuntimeError(f"No refresh_token for whoop_user_id={row.whoop_user_id}")

    access = row.access_token
    if access and not _access_token_needs_refresh(row.expires_at):
        return access

    try:
        token_json = exchange_refresh_token(
            refresh_token=row.refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
    except RuntimeError as e:
        upsert_whoop_token_row(
            database_url=database_url,
            state_label=row.state_label,
            whoop_user_id=row.whoop_user_id,
            refresh_token=row.refresh_token,
            access_token=row.access_token,
            expires_at=row.expires_at,
            scope=None,
            raw={"error": str(e)},
            needs_reconnect=True,
        )
        raise

    new_access = token_json.get("access_token")
    if not new_access or not isinstance(new_access, str):
        raise RuntimeError("Refresh response missing access_token")

    new_refresh = token_json.get("refresh_token") or row.refresh_token
    scope_s = token_json.get("scope")
    scope_str = scope_s if isinstance(scope_s, str) else None
    exp = expires_at_from_token_json(token_json)

    upsert_whoop_token_row(
        database_url=database_url,
        state_label=row.state_label,
        whoop_user_id=row.whoop_user_id,
        refresh_token=str(new_refresh) if new_refresh else None,
        access_token=new_access,
        expires_at=exp,
        scope=scope_str,
        raw=token_json,
        needs_reconnect=False,
    )
    return new_access


def _iso_range_utc(*, lookback_days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, lookback_days))
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    return start.strftime(fmt), end.strftime(fmt)


# Append-only (Medallion raw): requires schema/medallion_raw_layer_migration.sql applied.
INSERT_SLEEP = """
INSERT INTO public.whoop_sleep_staging (sleep_id, whoop_user_id, payload, synced_at, etl_ingested_at)
VALUES (%(sleep_id)s, %(whoop_user_id)s, %(payload)s, NOW(), NOW())
"""

INSERT_WORKOUT = """
INSERT INTO public.whoop_workout_staging (workout_id, whoop_user_id, payload, synced_at, etl_ingested_at)
VALUES (%(workout_id)s, %(whoop_user_id)s, %(payload)s, NOW(), NOW())
"""

INSERT_CYCLE = """
INSERT INTO public.whoop_cycle_staging (whoop_user_id, cycle_id, payload, synced_at, etl_ingested_at)
VALUES (%(whoop_user_id)s, %(cycle_id)s, %(payload)s, NOW(), NOW())
"""

INSERT_RECOVERY = """
INSERT INTO public.whoop_recovery_staging (whoop_user_id, cycle_id, payload, synced_at, etl_ingested_at)
VALUES (%(whoop_user_id)s, %(cycle_id)s, %(payload)s, NOW(), NOW())
"""


def _uuid_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _int_id(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def count_sleep(
    *,
    access_token: str,
    start: str,
    end: str,
) -> int:
    n = 0
    for rec in iter_collection_records(
        "/v2/activity/sleep",
        access_token=access_token,
        start=start,
        end=end,
    ):
        if _uuid_str(rec.get("id")):
            n += 1
    return n


def sync_sleep(
    conn: Any,
    *,
    whoop_user_id: str,
    access_token: str,
    start: str,
    end: str,
) -> int:
    batch: list[dict[str, Any]] = []
    for rec in iter_collection_records(
        "/v2/activity/sleep",
        access_token=access_token,
        start=start,
        end=end,
    ):
        sid = _uuid_str(rec.get("id"))
        if not sid:
            continue
        batch.append(
            {
                "sleep_id": sid,
                "whoop_user_id": whoop_user_id,
                "payload": Json(rec),
            }
        )
    if not batch:
        return 0
    with conn.cursor() as cur:
        execute_batch(cur, INSERT_SLEEP, batch, page_size=100)
    return len(batch)


def count_workout(
    *,
    access_token: str,
    start: str,
    end: str,
) -> int:
    n = 0
    for rec in iter_collection_records(
        "/v2/activity/workout",
        access_token=access_token,
        start=start,
        end=end,
    ):
        if _uuid_str(rec.get("id")):
            n += 1
    return n


def sync_workout(
    conn: Any,
    *,
    whoop_user_id: str,
    access_token: str,
    start: str,
    end: str,
) -> int:
    batch: list[dict[str, Any]] = []
    for rec in iter_collection_records(
        "/v2/activity/workout",
        access_token=access_token,
        start=start,
        end=end,
    ):
        wid = _uuid_str(rec.get("id"))
        if not wid:
            continue
        batch.append(
            {
                "workout_id": wid,
                "whoop_user_id": whoop_user_id,
                "payload": Json(rec),
            }
        )
    if not batch:
        return 0
    with conn.cursor() as cur:
        execute_batch(cur, INSERT_WORKOUT, batch, page_size=100)
    return len(batch)


def count_cycle(
    *,
    access_token: str,
    start: str,
    end: str,
) -> int:
    n = 0
    for rec in iter_collection_records(
        "/v2/cycle",
        access_token=access_token,
        start=start,
        end=end,
    ):
        if _int_id(rec.get("id")) is not None:
            n += 1
    return n


def sync_cycle(
    conn: Any,
    *,
    whoop_user_id: str,
    access_token: str,
    start: str,
    end: str,
) -> int:
    batch: list[dict[str, Any]] = []
    for rec in iter_collection_records(
        "/v2/cycle",
        access_token=access_token,
        start=start,
        end=end,
    ):
        cid = _int_id(rec.get("id"))
        if cid is None:
            continue
        batch.append(
            {
                "whoop_user_id": whoop_user_id,
                "cycle_id": cid,
                "payload": Json(rec),
            }
        )
    if not batch:
        return 0
    with conn.cursor() as cur:
        execute_batch(cur, INSERT_CYCLE, batch, page_size=100)
    return len(batch)


def count_recovery(
    *,
    access_token: str,
    start: str,
    end: str,
) -> int:
    n = 0
    for rec in iter_collection_records(
        "/v2/recovery",
        access_token=access_token,
        start=start,
        end=end,
    ):
        if _int_id(rec.get("cycle_id")) is not None:
            n += 1
    return n


def sync_recovery(
    conn: Any,
    *,
    whoop_user_id: str,
    access_token: str,
    start: str,
    end: str,
) -> int:
    batch: list[dict[str, Any]] = []
    for rec in iter_collection_records(
        "/v2/recovery",
        access_token=access_token,
        start=start,
        end=end,
    ):
        cid = _int_id(rec.get("cycle_id"))
        if cid is None:
            continue
        batch.append(
            {
                "whoop_user_id": whoop_user_id,
                "cycle_id": cid,
                "payload": Json(rec),
            }
        )
    if not batch:
        return 0
    with conn.cursor() as cur:
        execute_batch(cur, INSERT_RECOVERY, batch, page_size=100)
    return len(batch)


RESOURCE_SYNCERS = {
    "sleep": sync_sleep,
    "workout": sync_workout,
    "cycle": sync_cycle,
    "recovery": sync_recovery,
}

RESOURCE_COUNTERS = {
    "sleep": count_sleep,
    "workout": count_workout,
    "cycle": count_cycle,
    "recovery": count_recovery,
}


def run_etl(
    *,
    database_url: str,
    client_id: str,
    client_secret: str,
    lookback_days: int,
    resources: list[str],
    whoop_user_id: str | None,
    dry_run: bool,
    allowed_state_labels: set[str] | None = None,
) -> dict[str, Any]:
    """Sync WHOOP data for all linked users (or one). Returns summary dict."""
    start, end = _iso_range_utc(lookback_days=lookback_days)
    summary: dict[str, Any] = {
        "window_start": start,
        "window_end": end,
        "api_base": WHOOP_API_BASE,
        "users": [],
    }

    rows = load_token_rows(
        database_url,
        whoop_user_id=whoop_user_id,
        allowed_state_labels=allowed_state_labels,
    )
    if not rows:
        summary["error"] = "No token rows with refresh_token (needs_reconnect=false)."
        return summary

    for row in rows:
        user_entry: dict[str, Any] = {
            "whoop_user_id": row.whoop_user_id,
            "counts": {},
            "error": None,
        }
        try:
            if dry_run:
                access = row.access_token or ""
                if not access or _access_token_needs_refresh(row.expires_at):
                    user_entry["error"] = (
                        "Dry-run needs a non-expired access_token in DB (run a full sync once, "
                        "or omit --dry-run to refresh)."
                    )
                    summary["users"].append(user_entry)
                    continue
                counts: dict[str, int] = {}
                for res in resources:
                    fn = RESOURCE_COUNTERS.get(res)
                    if not fn:
                        continue
                    counts[res] = fn(
                        access_token=access,
                        start=start,
                        end=end,
                    )
                user_entry["counts"] = counts
                user_entry["note"] = "dry-run: API counts only; no staging writes"
                summary["users"].append(user_entry)
                continue

            access = refresh_and_persist_tokens(
                row,
                client_id=client_id,
                client_secret=client_secret,
                database_url=database_url,
            )

            conn = psycopg2.connect(database_url)
            try:
                counts: dict[str, int] = {}
                for res in resources:
                    fn = RESOURCE_SYNCERS.get(res)
                    if not fn:
                        continue
                    n = fn(
                        conn,
                        whoop_user_id=row.whoop_user_id,
                        access_token=access,
                        start=start,
                        end=end,
                    )
                    counts[res] = n
                conn.commit()
                user_entry["counts"] = counts
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except Exception as e:
            user_entry["error"] = str(e)
        summary["users"].append(user_entry)

    return summary


def whoop_credentials_from_env() -> tuple[str, str]:
    cid = _clean_oauth_value(os.getenv("WHOOP_CLIENT_ID", ""))
    sec = _clean_oauth_value(os.getenv("WHOOP_CLIENT_SECRET", ""))
    if not cid or not sec:
        raise RuntimeError("WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET are required.")
    return cid, sec
