"""
Ingest VALD External ForceFrame test summaries (GET /tests/v2) into public.vald_forceframe_tests_staging.

This is activity / performance data (jumps, forces, impulses, etc.), not the Profiles API.

Prerequisites:
  - schema/vald_forceframe_tests_staging.sql applied in Supabase.
  - Same VALD OAuth as profiles: VALD_CLIENT_ID, VALD_CLIENT_SECRET.
  - VALD_API_BASE_FORCEFRAME (default AUE) if your tenant is in another region.

Run:
  python upload_vald_forceframe_tests_to_supabase.py
  python upload_vald_forceframe_tests_to_supabase.py --tenant-id <uuid> --lookback-days 14

Env:
  SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS — default lookback for ModifiedFromUtc (default 7).
  ROSTER_FILTER=1 — when set with allowlist, one API call per roster VALD profile id (recommended).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

from integrations import config
from integrations.roster_allowlist import env_roster_filter_enabled, load_roster_allowlist
from integrations.vald.client import ValdClient

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "").strip()

INSERT_SQL = """
INSERT INTO public.vald_forceframe_tests_staging (
    tenant_id, test_id, profile_id, test_date_utc, test_type_name, payload, synced_at, etl_ingested_at
) VALUES (
    %(tenant_id)s, %(test_id)s::uuid, %(profile_id)s::uuid, %(test_date_utc)s, %(test_type_name)s,
    %(payload)s, NOW(), NOW()
)
"""


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_ts(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _tests_from_response(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    t = data.get("tests")
    if not isinstance(t, list):
        return []
    return [x for x in t if isinstance(x, dict)]


def _parse_uuid(val: Any) -> uuid.UUID | None:
    if val is None:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


def map_test_row(tenant_id: str, item: dict[str, Any]) -> dict[str, Any] | None:
    tid = _parse_uuid(item.get("testId") or item.get("test_id"))
    if tid is None:
        return None
    pid = _parse_uuid(item.get("profileId") or item.get("profile_id"))
    tdu = _parse_ts(item.get("testDateUtc") or item.get("test_date_utc"))
    tname = item.get("testTypeName") or item.get("test_type_name")
    if tname is not None:
        tname = str(tname)
    return {
        "tenant_id": tenant_id.strip(),
        "test_id": str(tid),
        "profile_id": pid,
        "test_date_utc": tdu,
        "test_type_name": tname,
        "payload": Json(item),
    }


def tenant_ids_from_client(client: ValdClient, single: str | None) -> list[str]:
    if single and single.strip():
        return [single.strip()]
    raw = client.list_tenants()
    ids: list[str] = []
    if isinstance(raw, list):
        for t in raw:
            if isinstance(t, dict) and t.get("id") is not None:
                ids.append(str(t["id"]))
    elif isinstance(raw, dict):
        inner = raw.get("tenants") or raw.get("items") or raw.get("data")
        if isinstance(inner, list):
            for t in inner:
                if isinstance(t, dict) and t.get("id") is not None:
                    ids.append(str(t["id"]))
    return ids


def modified_from_iso(lookback_days: int) -> str:
    n = max(1, lookback_days)
    start = datetime.now(timezone.utc) - timedelta(days=n)
    return start.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append VALD ForceFrame /tests/v2 rows into Supabase (raw layer)"
    )
    parser.add_argument("--tenant-id", default="", help="Only this tenant UUID")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=_env_int("SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS", 7),
        help="How far back ModifiedFromUtc reaches (default 7 or SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS)",
    )
    args = parser.parse_args()

    if not DB_URL:
        print("[ERROR] DATABASE_URL not set in .env", file=sys.stderr)
        return 1

    ff_base = config.vald_settings().get("api_base_forceframe", "").strip()
    print(f"[INFO] ForceFrame API base: {ff_base}", file=sys.stderr)

    try:
        client = ValdClient()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    tids = tenant_ids_from_client(client, args.tenant_id or None)
    if not tids:
        print("[ERROR] No tenant ids returned.", file=sys.stderr)
        return 1

    modified_iso = modified_from_iso(args.lookback_days)
    print(
        f"[INFO] ForceFrame GET /tests/v2 ModifiedFromUtc={modified_iso} "
        f"(lookback_days={args.lookback_days})",
        file=sys.stderr,
    )

    profile_loops: list[str | None]
    if env_roster_filter_enabled():
        try:
            _, roster = load_roster_allowlist()
        except FileNotFoundError as e:
            print(f"[ERROR] ROSTER_FILTER=1 but roster workbook missing: {e}", file=sys.stderr)
            return 1
        pids = sorted({str(x).strip() for x in roster.vald_profile_ids if str(x).strip()})
        if not pids:
            print(
                "[WARN] ROSTER_FILTER=1 but no Vald Profile_ID in workbook; "
                "fetching tenant-wide (no ProfileId filter).",
                file=sys.stderr,
            )
            profile_loops = [None]
        else:
            profile_loops = pids
            print(
                f"[INFO] ROSTER_FILTER: {len(profile_loops)} profile id(s) for ForceFrame pull.",
                file=sys.stderr,
            )
    else:
        profile_loops = [None]

    ok = 0
    skipped = 0
    api_errors = 0
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        for tid in tids:
            for prof in profile_loops:
                try:
                    raw = client.list_tests_modified_since(tid, modified_iso, profile_id=prof)
                except Exception as e:
                    print(f"  [WARNING] tenant {tid} profile={prof!r}: API {e}", file=sys.stderr)
                    api_errors += 1
                    continue
                tests = _tests_from_response(raw)
                if prof:
                    print(f"  [INFO] tenant {tid} profile {prof}: {len(tests)} test(s)", file=sys.stderr)
                else:
                    print(f"  [INFO] tenant {tid}: {len(tests)} test(s)", file=sys.stderr)
                for item in tests:
                    mapped = map_test_row(tid, item)
                    if not mapped:
                        skipped += 1
                        continue
                    try:
                        cur.execute(INSERT_SQL, mapped)
                        ok += 1
                    except Exception as e:
                        print(f"  [WARNING] skip test row: {e}", file=sys.stderr)
                        skipped += 1
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database error: {e}", file=sys.stderr)
        return 1

    print(f"\n[SUCCESS] Inserted {ok} ForceFrame test row(s); skipped {skipped}; API errors {api_errors}.")
    print("[CHECK] SELECT MAX(etl_ingested_at), COUNT(*) FROM public.vald_forceframe_tests_staging;")
    if ok == 0 and api_errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
