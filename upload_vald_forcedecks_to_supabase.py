"""
Ingest VALD External ForceDecks data (matches Volleyball AU / Uni package grain).

1) GET /tests into public.vald_forcedecks_tests_staging (same idea as VA_VALD_Tests.xlsx).
2) If VALD_FORCEDECKS_TEAM_ID is set: GET .../tests/detailed/{from}/{to} into
   public.vald_forcedecks_trials_staging (VA_VALD_Trials).
3) If VALD_FORCEDECKS_SYNC_DEFINITIONS=1: GET /resultdefinitions into vald_forcedecks_result_definitions_staging.

Prerequisites: apply schema/*.sql for the three tables. Same OAuth as other VALD scripts.

Env:
  VALD_API_BASE_FORCEDECKS — default AUE extforcedecks host (see .env.example).
  SCHEDULED_VALD_FORCEDECKS_LOOKBACK_DAYS — falls back to SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS then 7.
  VALD_FORCEDECKS_TEAM_ID — optional UUID; required path segment for detailed tests + embedded trials.
  VALD_FORCEDECKS_SYNC_DEFINITIONS — set to 1 to pull /resultdefinitions each run.

Run from repo root:
  python upload_vald_forcedecks_to_supabase.py
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

INSERT_TEST = """
INSERT INTO public.vald_forcedecks_tests_staging (
    tenant_id, test_id, profile_id, recording_id, test_type,
    modified_date_utc, recorded_date_utc, payload, synced_at, etl_ingested_at
) VALUES (
    %(tenant_id)s::uuid, %(test_id)s::uuid, %(profile_id)s::uuid, %(recording_id)s::uuid, %(test_type)s,
    %(modified_date_utc)s, %(recorded_date_utc)s, %(payload)s, NOW(), NOW()
)
"""

INSERT_TRIAL = """
INSERT INTO public.vald_forcedecks_trials_staging (
    team_id, test_id, trial_id, athlete_id, payload, synced_at, etl_ingested_at
) VALUES (
    %(team_id)s::uuid, %(test_id)s::uuid, %(trial_id)s::uuid, %(athlete_id)s::uuid, %(payload)s, NOW(), NOW()
)
"""

INSERT_DEF = """
INSERT INTO public.vald_forcedecks_result_definitions_staging (
    result_id, payload, synced_at, etl_ingested_at
) VALUES (
    %(result_id)s, %(payload)s, NOW(), NOW()
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


def _parse_uuid(val: Any) -> uuid.UUID | None:
    if val is None:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


def _tests_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        t = data.get("tests")
        if isinstance(t, list):
            return [x for x in t if isinstance(x, dict)]
    return []


def _uuid_str(u: uuid.UUID | None) -> str | None:
    """psycopg2 (without register_uuid) cannot adapt uuid.UUID; pass text for ::uuid casts."""
    return str(u) if u is not None else None


def map_test_row(item: dict[str, Any]) -> dict[str, Any] | None:
    tid = _parse_uuid(item.get("testId"))
    if tid is None:
        return None
    ten = _parse_uuid(item.get("tenantId"))
    if ten is None:
        return None
    return {
        "tenant_id": _uuid_str(ten),
        "test_id": _uuid_str(tid),
        "profile_id": _uuid_str(_parse_uuid(item.get("profileId"))),
        "recording_id": _uuid_str(_parse_uuid(item.get("recordingId"))),
        "test_type": item.get("testType"),
        "modified_date_utc": _parse_ts(item.get("modifiedDateUtc")),
        "recorded_date_utc": _parse_ts(item.get("recordedDateUtc")),
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


def date_range_iso(lookback_days: int) -> tuple[str, str]:
    """UTC [start, end] for detailed tests path (inclusive window)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, lookback_days))
    s = start.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    e = end.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return s, e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ForceDecks to Supabase (VA package-aligned grain)"
    )
    parser.add_argument("--tenant-id", default="", help="Limit tenant list to this UUID")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=_env_int(
            "SCHEDULED_VALD_FORCEDECKS_LOOKBACK_DAYS",
            _env_int("SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS", 7),
        ),
        help="ModifiedFromUtc lookback and detailed date window width (days)",
    )
    args = parser.parse_args()

    if not DB_URL:
        print("[ERROR] DATABASE_URL not set", file=sys.stderr)
        return 1

    fd = config.vald_settings().get("api_base_forcedecks", "").strip()
    print(f"[INFO] ForceDecks API base: {fd}", file=sys.stderr)

    try:
        client = ValdClient()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    tids = tenant_ids_from_client(client, args.tenant_id or None)
    if not tids:
        print("[ERROR] No tenants from API", file=sys.stderr)
        return 1

    modified_iso = modified_from_iso(args.lookback_days)
    print(
        f"[INFO] GET /tests ModifiedFromUtc={modified_iso} (lookback_days={args.lookback_days})",
        file=sys.stderr,
    )

    profile_loops: list[str | None]
    if env_roster_filter_enabled():
        try:
            _, roster = load_roster_allowlist()
        except FileNotFoundError as e:
            print(f"[ERROR] ROSTER_FILTER=1 but roster missing: {e}", file=sys.stderr)
            return 1
        pids = sorted({str(x).strip() for x in roster.vald_profile_ids if str(x).strip()})
        profile_loops = pids if pids else [None]
        if pids:
            print(f"[INFO] ROSTER_FILTER: {len(pids)} VALD profile id(s)", file=sys.stderr)
    else:
        profile_loops = [None]

    ok_tests = 0
    ok_trials = 0
    api_err = 0
    team_raw = os.getenv("VALD_FORCEDECKS_TEAM_ID", "").strip()
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        for tenant in tids:
            for prof in profile_loops:
                try:
                    raw = client.list_forcedecks_tests_modified_since(
                        tenant, modified_iso, profile_id=prof
                    )
                except Exception as e:
                    print(f"  [WARN] /tests tenant={tenant} profile={prof!r}: {e}", file=sys.stderr)
                    api_err += 1
                    continue
                for item in _tests_payload(raw):
                    mapped = map_test_row(item)
                    if not mapped:
                        continue
                    try:
                        cur.execute(INSERT_TEST, mapped)
                        ok_tests += 1
                    except Exception as e:
                        print(f"  [WARN] test insert: {e}", file=sys.stderr)

        if team_raw:
            d0, d1 = date_range_iso(args.lookback_days)
            print(
                f"[INFO] Detailed tests + trials team={team_raw} window {d0} .. {d1}",
                file=sys.stderr,
            )
            try:
                detailed_list = client.list_forcedecks_detailed_tests_date_range(team_raw, d0, d1)
            except Exception as e:
                print(f"[WARN] detailed tests fetch: {e}", file=sys.stderr)
                api_err += 1
                detailed_list = []
            team_uuid = _parse_uuid(team_raw)
            if team_uuid and isinstance(detailed_list, list):
                for dt in detailed_list:
                    if not isinstance(dt, dict):
                        continue
                    test_uid = _parse_uuid(dt.get("id"))
                    if test_uid is None:
                        continue
                    for tr in dt.get("trials") or []:
                        if not isinstance(tr, dict):
                            continue
                        trial_uid = _parse_uuid(tr.get("id"))
                        if trial_uid is None:
                            continue
                        ath = _parse_uuid(tr.get("athleteId") or dt.get("athleteId"))
                        try:
                            cur.execute(
                                INSERT_TRIAL,
                                {
                                    "team_id": _uuid_str(team_uuid),
                                    "test_id": _uuid_str(test_uid),
                                    "trial_id": _uuid_str(trial_uid),
                                    "athlete_id": _uuid_str(ath),
                                    "payload": Json(tr),
                                },
                            )
                            ok_trials += 1
                        except Exception as e:
                            print(f"  [WARN] trial insert: {e}", file=sys.stderr)
        else:
            print(
                "[INFO] VALD_FORCEDECKS_TEAM_ID unset — skipping detailed tests/trials "
                "(set team UUID from VALD Hub / package context to load VA_VALD_Trials-equivalent).",
                file=sys.stderr,
            )

        if os.getenv("VALD_FORCEDECKS_SYNC_DEFINITIONS", "").strip() in ("1", "true", "yes"):
            try:
                defs = client.list_forcedecks_result_definitions()
            except Exception as e:
                print(f"[WARN] resultdefinitions: {e}", file=sys.stderr)
                defs = {}
            rows = defs.get("resultDefinitions") if isinstance(defs, dict) else None
            if isinstance(rows, list):
                for d in rows:
                    if not isinstance(d, dict):
                        continue
                    rid = d.get("resultId")
                    if rid is None:
                        continue
                    try:
                        cur.execute(INSERT_DEF, {"result_id": int(rid), "payload": Json(d)})
                    except Exception as e:
                        print(f"  [WARN] definition insert: {e}", file=sys.stderr)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(
        f"\n[SUCCESS] ForceDecks: tests inserted={ok_tests}; "
        f"trials inserted={ok_trials if team_raw else 0} (team set={bool(team_raw)}); api_errors={api_err}"
    )
    if ok_tests == 0 and api_err > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
