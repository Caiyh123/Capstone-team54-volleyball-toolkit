"""
Scheduled WHOOP ETL: refresh OAuth tokens; pull v2 collections into staging tables (append-only inserts).

Requires .env:
  DATABASE_URL, WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET

Prerequisites:
  1. schema/whoop_oauth_tokens.sql
  2. schema/whoop_staging.sql

Examples:
  python whoop_etl.py
  python whoop_etl.py --lookback-days 7 --resources sleep,recovery
  python whoop_etl.py --whoop-user-id 12345
  python whoop_etl.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

load_dotenv()

from integrations.roster_allowlist import (
    env_roster_filter_enabled,
    load_roster_allowlist,
    whoop_allowed_state_labels,
)
from integrations.whoop.etl import (
    RESOURCE_SYNCERS,
    run_etl,
    whoop_credentials_from_env,
)


def _insert_etl_run(database_url: str, summary: dict[str, Any]) -> None:
    lookback = summary.get("lookback_days")
    ws = summary.get("window_start")
    we = summary.get("window_end")
    ok = True
    if summary.get("error"):
        ok = False
    for u in summary.get("users") or []:
        if u.get("error"):
            ok = False
            break
    conn = psycopg2.connect(database_url)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.whoop_etl_run (
                lookback_days, window_start, window_end, ok, summary
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (lookback, ws, we, ok, Json(summary)),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="WHOOP to Supabase staging ETL")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=int(os.getenv("WHOOP_ETL_LOOKBACK_DAYS", "14")),
        help="API window [now-lookback, now] in UTC (default 14 or WHOOP_ETL_LOOKBACK_DAYS)",
    )
    parser.add_argument(
        "--resources",
        default=os.getenv("WHOOP_ETL_RESOURCES", "sleep,workout,cycle,recovery"),
        help="Comma-separated: sleep,workout,cycle,recovery (default: all)",
    )
    parser.add_argument(
        "--whoop-user-id",
        default="",
        help="Only sync this WHOOP user id (default: all linked users)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count records via API without writing staging tables (needs valid access_token in DB)",
    )
    args = parser.parse_args()

    db = os.getenv("DATABASE_URL", "").strip()
    if not db:
        print("[ERROR] DATABASE_URL is not set.", file=sys.stderr)
        return 1

    res_list = [x.strip().lower() for x in args.resources.split(",") if x.strip()]
    valid = set(RESOURCE_SYNCERS.keys())
    unknown = [r for r in res_list if r not in valid]
    if unknown:
        print(f"[ERROR] Unknown resources: {unknown}. Valid: {sorted(valid)}", file=sys.stderr)
        return 1
    if not res_list:
        print("[ERROR] No resources selected.", file=sys.stderr)
        return 1

    try:
        cid, sec = whoop_credentials_from_env()
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    allowed_states: set[str] | None = None
    if env_roster_filter_enabled():
        _, roster = load_roster_allowlist()
        allowed_states = whoop_allowed_state_labels(roster)
        if not allowed_states:
            print("[ERROR] ROSTER_FILTER=1 but roster workbook has no GymAware IDs.", file=sys.stderr)
            return 1
        print(
            f"[INFO] ROSTER_FILTER: WHOOP ETL limited to {len(allowed_states)} linked account(s) "
            f"(state_label must match roster GymAware ID)."
        )

    summary = run_etl(
        database_url=db,
        client_id=cid,
        client_secret=sec,
        lookback_days=max(1, args.lookback_days),
        resources=res_list,
        whoop_user_id=args.whoop_user_id.strip() or None,
        dry_run=args.dry_run,
        allowed_state_labels=allowed_states,
    )
    summary["lookback_days"] = max(1, args.lookback_days)
    summary["resources"] = res_list

    print(json.dumps(summary, indent=2, default=str))

    if summary.get("error"):
        return 1

    if not args.dry_run:
        try:
            _insert_etl_run(db, summary)
        except Exception as e:
            print(f"[WARN] Could not write whoop_etl_run: {e}", file=sys.stderr)

    for u in summary.get("users") or []:
        if u.get("error"):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
