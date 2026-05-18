"""
Export GymAware Cloud summaries, reps, athletes, and personal bests for a UTC date range.

API (same Account ID + token for all):
  GET /summaries, /reps  — start/end windows (max ~1 month per request; chunked)
  GET /bests             — start/end (max ~3 months per request; chunked at 90 days by default)
  GET /athletes          — full roster snapshot (filtered to allowlist when enabled)

Roster: set ROSTER_FILTER=1 or GYMAWARE_USE_ALLOWLIST=1 (see integrations/gymaware/allowlist.py).

Run: python gymaware_export.py
      python gymaware_export.py --start 2026-03-01 --end 2026-03-28
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

CHUNK_DAYS = 28
# GymAware /bests allows ~3 months per request; default chunk is 90 days (override via env).
BESTS_CHUNK_DAYS = int(os.getenv("GYMAWARE_BESTS_CHUNK_DAYS", "90"))
SUMMARIES_OUT = "gymaware_summaries_export.json"
REPS_OUT = "gymaware_reps_export.json"
ATHLETES_OUT = "gymaware_athletes_export.json"
BESTS_OUT = "gymaware_bests_export.json"


def _parse_ymd(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)


def range_to_unix_pair(start_s: str, end_s: str) -> tuple[float, float]:
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


def dedupe_bests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("athleteReference"),
            row.get("exerciseName"),
            row.get("barWeight"),
        )
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
    *,
    dedupe_fn: Any = dedupe_by_reference,
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
    return dedupe_fn(all_rows)


def filter_athletes(rows: list[dict[str, Any]], allow_refs: set[int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ar = row.get("athleteReference")
        try:
            ar_int = int(ar) if ar is not None else None
        except (TypeError, ValueError):
            continue
        if ar_int is not None and ar_int in allow_refs:
            out.append(row)
    return out


def filter_bests(rows: list[dict[str, Any]], allow_refs: set[int]) -> list[dict[str, Any]]:
    return filter_rows_by_athlete_reference(rows, allow_refs)


def default_date_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    return start.isoformat(), end.isoformat()


def _write_json(path: str, rows: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"[SUCCESS] Wrote {len(rows)} row(s) to {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export GymAware summaries, reps, athletes, and bests to JSON."
    )
    parser.add_argument("--start", help="Start date UTC YYYY-MM-DD")
    parser.add_argument("--end", help="End date UTC YYYY-MM-DD inclusive")
    parser.add_argument(
        "--skip-reps",
        action="store_true",
        help="Skip GET /reps export",
    )
    parser.add_argument(
        "--skip-bests",
        action="store_true",
        help="Skip GET /bests export",
    )
    parser.add_argument(
        "--skip-athletes",
        action="store_true",
        help="Skip GET /athletes export",
    )
    parser.add_argument("--pause", type=float, default=1.0, help="Seconds between chunks")
    al = parser.add_mutually_exclusive_group()
    al.add_argument("--allowlist", action="store_true", help="Filter to roster workbook IDs")
    al.add_argument("--no-allowlist", action="store_true", help="Disable roster filter")
    args = parser.parse_args()

    start_s = args.start or os.getenv("GYMAWARE_EXPORT_START", "").strip()
    end_s = args.end or os.getenv("GYMAWARE_EXPORT_END", "").strip()
    if not start_s or not end_s:
        start_s, end_s = default_date_range()
        print(f"[INFO] No date range set; using default UTC window {start_s} .. {end_s}")

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

    summary_windows = iter_chunks(start_ts, end_ts, CHUNK_DAYS * 86400)
    bests_windows = iter_chunks(start_ts, end_ts, BESTS_CHUNK_DAYS * 86400)
    if not summary_windows:
        print("[ERROR] Empty date range.")
        return 1

    try:
        client = GymAwareClient()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 1

    allow_refs: set[int] | None = None
    if use_allowlist:
        try:
            _, allow_refs = load_athlete_references_from_xlsx()
        except FileNotFoundError as e:
            print(f"[ERROR] Roster filter enabled but workbook missing: {e}")
            return 1
        if not allow_refs:
            print("[ERROR] Roster filter enabled but workbook contains no GymAware IDs.")
            return 1
        print(f"[INFO] ROSTER_FILTER: GymAware export limited to {len(allow_refs)} athlete reference(s).")

    print(f"[INFO] GymAware export UTC range (inclusive dates): {start_s} .. {end_s}\n")

    summaries = export_resource(
        "summaries",
        client.list_summaries,
        summary_windows,
        args.pause,
    )
    if use_allowlist and allow_refs is not None:
        before = len(summaries)
        summaries = filter_rows_by_athlete_reference(summaries, allow_refs)
        print(f"[INFO] summaries allowlist: {len(summaries)} / {before} row(s)")
    _write_json(SUMMARIES_OUT, summaries)

    if not args.skip_reps:
        reps = export_resource("reps", client.list_reps, summary_windows, args.pause)
        if use_allowlist and allow_refs is not None:
            before = len(reps)
            reps = filter_rows_by_athlete_reference(reps, allow_refs)
            print(f"[INFO] reps allowlist: {len(reps)} / {before} row(s)")
        _write_json(REPS_OUT, reps)

    if not args.skip_athletes:
        print("[INFO] Fetching athletes (full list)...")
        athletes = client.list_athletes()
        if use_allowlist and allow_refs is not None:
            before = len(athletes)
            athletes = filter_athletes(athletes, allow_refs)
            print(f"[INFO] athletes allowlist: {len(athletes)} / {before} row(s)")
        _write_json(ATHLETES_OUT, athletes)

    if not args.skip_bests:
        bests = export_resource(
            "bests",
            client.list_bests,
            bests_windows,
            args.pause,
            dedupe_fn=dedupe_bests,
        )
        if use_allowlist and allow_refs is not None:
            before = len(bests)
            bests = filter_bests(bests, allow_refs)
            print(f"[INFO] bests allowlist: {len(bests)} / {before} row(s)")
        _write_json(BESTS_OUT, bests)

    return 0


if __name__ == "__main__":
    sys.exit(main())
