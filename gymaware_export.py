"""
Export GymAware Cloud summaries (and optionally reps) for a UTC date range.

API: GET /summaries and GET /reps require paired start/end (Unix seconds UTC).
Docs cap each request at ~1 month; this script chunks windows safely.

Configure via .env or CLI:
  GYMAWARE_EXPORT_START=2026-01-01
  GYMAWARE_EXPORT_END=2026-01-31
  GYMAWARE_INCLUDE_REPS=0   # set 1 to also write gymaware_reps_export.json
  GYMAWARE_USE_ALLOWLIST=1  # optional: filter to workbook IDs (see integrations/gymaware/allowlist.py)

Run: python gymaware_export.py
      python gymaware_export.py --start 2026-03-01 --end 2026-03-28
      python gymaware_export.py --allowlist
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from integrations.gymaware.allowlist import (
    env_use_allowlist,
    filter_rows_by_athlete_reference,
    load_athlete_references_from_xlsx,
)
from integrations.gymaware.client import GymAwareClient

# Stay under GymAware "max 1 month per request" guidance
CHUNK_DAYS = 28
SUMMARIES_OUT = "gymaware_summaries_export.json"
REPS_OUT = "gymaware_reps_export.json"


def _parse_ymd(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)


def range_to_unix_pair(start_s: str, end_s: str) -> tuple[float, float]:
    """Inclusive calendar dates in UTC -> [start_midnight, end_next_midnight) in unix seconds."""
    start_dt = _parse_ymd(start_s)
    end_dt = _parse_ymd(end_s)
    if end_dt < start_dt:
        raise ValueError("end date must be on or after start date")
    start_ts = start_dt.timestamp()
    end_exclusive = (end_dt + timedelta(days=1)).timestamp()
    return start_ts, end_exclusive


def iter_chunks(start_ts: float, end_ts: float, chunk_seconds: float) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    cursor = start_ts
    while cursor < end_ts - 1e-6:
        nxt = min(cursor + chunk_seconds, end_ts)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows


def dedupe_by_reference(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        ref = row.get("reference")
        key = str(ref) if ref is not None else json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def export_resource(
    label: str,
    fetcher: Any,
    windows: list[tuple[float, float]],
    pause_s: float,
) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    for i, (s, e) in enumerate(windows):
        print(
            f"[INFO] {label} chunk {i + 1}/{len(windows)}: "
            f"{datetime.fromtimestamp(s, tz=timezone.utc).date()} -> "
            f"{datetime.fromtimestamp(e, tz=timezone.utc).date()} (UTC)"
        )
        chunk = fetcher(start=s, end=e)
        if chunk:
            all_rows.extend(chunk)
        if i < len(windows) - 1 and pause_s > 0:
            time.sleep(pause_s)
    return dedupe_by_reference(all_rows)


def default_date_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    return start.isoformat(), end.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export GymAware summaries/reps to JSON.")
    parser.add_argument("--start", help="Start date UTC YYYY-MM-DD (default: env or last 7 days)")
    parser.add_argument("--end", help="End date UTC YYYY-MM-DD inclusive (default: today UTC)")
    parser.add_argument(
        "--include-reps",
        action="store_true",
        help="Also export /reps to gymaware_reps_export.json",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=1.0,
        help="Seconds between chunk requests (default: 1)",
    )
    al = parser.add_mutually_exclusive_group()
    al.add_argument(
        "--allowlist",
        action="store_true",
        help="Filter rows to athlete IDs in the allowlist workbook (see GYMAWARE_ALLOWLIST_XLSX)",
    )
    al.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Do not filter by allowlist (overrides GYMAWARE_USE_ALLOWLIST in .env)",
    )
    args = parser.parse_args()

    start_s = args.start or os.getenv("GYMAWARE_EXPORT_START", "").strip()
    end_s = args.end or os.getenv("GYMAWARE_EXPORT_END", "").strip()
    if not start_s or not end_s:
        start_s, end_s = default_date_range()
        print(f"[INFO] No date range set; using default UTC window {start_s} .. {end_s}")

    include_reps = args.include_reps or os.getenv("GYMAWARE_INCLUDE_REPS", "").strip() in (
        "1",
        "true",
        "yes",
    )

    if args.no_allowlist:
        use_allowlist = False
    elif args.allowlist:
        use_allowlist = True
    else:
        use_allowlist = env_use_allowlist()

    try:
        start_ts, end_ts = range_to_unix_pair(start_s, end_s)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1

    chunk_seconds = CHUNK_DAYS * 86400
    windows = iter_chunks(start_ts, end_ts, chunk_seconds)
    if not windows:
        print("[ERROR] Empty date range.")
        return 1

    try:
        client = GymAwareClient()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 1

    print(f"[INFO] GymAware export UTC range (inclusive dates): {start_s} .. {end_s}")
    print(f"[INFO] {len(windows)} API chunk(s) (max ~{CHUNK_DAYS} days each)\n")

    allow_refs: set[int] | None = None
    if use_allowlist:
        try:
            _, allow_refs = load_athlete_references_from_xlsx()
        except FileNotFoundError as e:
            print(f"[ERROR] Allowlist enabled but workbook missing: {e}")
            return 1
        if not allow_refs:
            print("[ERROR] Allowlist enabled but workbook contains no athlete IDs.")
            return 1

    summaries = export_resource(
        "summaries",
        client.list_summaries,
        windows,
        args.pause,
    )
    if use_allowlist and allow_refs is not None:
        before = len(summaries)
        summaries = filter_rows_by_athlete_reference(summaries, allow_refs)
        print(
            f"[INFO] Allowlist filter: {len(summaries)} summary row(s) kept "
            f"(from {before} before filter)"
        )

    with open(SUMMARIES_OUT, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)
    print(f"\n[SUCCESS] Wrote {len(summaries)} summary row(s) to {SUMMARIES_OUT}")

    if include_reps:
        reps = export_resource(
            "reps",
            client.list_reps,
            windows,
            args.pause,
        )
        if use_allowlist and allow_refs is not None:
            before_r = len(reps)
            reps = filter_rows_by_athlete_reference(reps, allow_refs)
            print(
                f"[INFO] Allowlist filter: {len(reps)} rep row(s) kept "
                f"(from {before_r} before filter)"
            )
        with open(REPS_OUT, "w", encoding="utf-8") as f:
            json.dump(reps, f, indent=2)
        print(f"[SUCCESS] Wrote {len(reps)} rep row(s) to {REPS_OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
