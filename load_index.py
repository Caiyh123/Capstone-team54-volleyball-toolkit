"""
Catapult Load Index (date range in UTC):

    Load Index = Sum(total_player_load) / Total jump count

Jump count uses the same source as `Jump Data - BEACH VB.R`:
GET .../activities/{id}/athletes/{aid}/events?event_types=basketball
Rows with jump_attribute > 0 after data/basketball unnesting logic.

Requires: CATAPULT_TOKEN, CATAPULT_BASE_URL in .env

Run:
  python load_index.py --start 2026-03-01 --end 2026-03-28
  python load_index.py --start 2026-03-24 --end 2026-03-24 --max-activities 1  # quick smoke test
  python load_index.py   # uses CATAPULT_LOAD_INDEX_START / END or last 7 days UTC
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

from integrations import config

PAUSE_S = float(os.getenv("CATAPULT_API_PAUSE", "0.5"))


def _activity_date(act: dict[str, Any]) -> datetime | None:
    st = act.get("start_time")
    if st is None:
        return None
    try:
        return datetime.fromtimestamp(float(st), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


def fetch_activities(headers: dict[str, str], base: str) -> list[dict[str, Any]]:
    r = requests.get(f"{base}/activities", headers=headers, timeout=120)
    r.raise_for_status()
    raw = r.json()
    acts = raw.get("data", raw) if isinstance(raw, dict) else raw
    return acts if isinstance(acts, list) else []


def activities_in_range(
    activities: list[dict[str, Any]], start_d: datetime.date, end_d: datetime.date
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for act in activities:
        d = _activity_date(act)
        if d is not None and start_d <= d <= end_d:
            out.append(act)
    return out


def sum_player_load_for_activity(
    headers: dict[str, str], base: str, activity_id: str
) -> float:
    payload = {
        "group_by": ["participating_athlete"],
        "filters": [
            {
                "name": "activity_id",
                "comparison": "=",
                "values": [activity_id],
            }
        ],
    }
    r = requests.post(f"{base}/stats", headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        print(f"  [WARN] stats HTTP {r.status_code} for activity {activity_id}")
        return 0.0
    raw = r.json()
    rows = raw if isinstance(raw, list) else raw.get("data", []) if isinstance(raw, dict) else []
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        v = row.get("total_player_load")
        if v is not None:
            try:
                total += float(v)
            except (TypeError, ValueError):
                pass
    return total


def fetch_activity_athletes(
    headers: dict[str, str], base: str, activity_id: str
) -> list[dict[str, Any]]:
    r = requests.get(
        f"{base}/activities/{activity_id}/athletes",
        headers=headers,
        timeout=120,
    )
    if r.status_code != 200:
        print(f"  [WARN] athletes HTTP {r.status_code} for activity {activity_id}")
        return []
    raw = r.json()
    rows = raw if isinstance(raw, list) else raw.get("data", raw) if isinstance(raw, dict) else []
    return rows if isinstance(rows, list) else []


def iter_jump_records(payload: Any) -> Any:
    """Mirror R unnest(data) then unnest(basketball); yield leaf dicts."""
    if payload is None:
        return
    if isinstance(payload, dict):
        if payload.get("data") is not None:
            d = payload["data"]
            if isinstance(d, list):
                for item in d:
                    yield from iter_jump_records(item)
            else:
                yield from iter_jump_records(d)
            return
        if payload.get("basketball") is not None:
            b = payload["basketball"]
            if isinstance(b, list):
                for item in b:
                    yield from iter_jump_records(item)
            else:
                yield from iter_jump_records(b)
            return
        yield payload
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_jump_records(item)


def count_jumps_in_events_payload(payload: Any) -> int:
    n = 0
    for rec in iter_jump_records(payload):
        if not isinstance(rec, dict):
            continue
        if "jump_attribute" not in rec:
            continue
        try:
            if float(rec.get("jump_attribute") or 0) > 0:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def fetch_jump_count_for_athlete(
    headers: dict[str, str], base: str, activity_id: str, athlete_id: str
) -> int:
    url = f"{base}/activities/{activity_id}/athletes/{athlete_id}/events"
    r = requests.get(
        url,
        headers=headers,
        params={"event_types": "basketball"},
        timeout=120,
    )
    if r.status_code != 200:
        return 0
    try:
        body = r.json()
    except json.JSONDecodeError:
        return 0
    return count_jumps_in_events_payload(body)


def default_range() -> tuple[datetime.date, datetime.date]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    return start, end


def main() -> int:
    parser = argparse.ArgumentParser(description="Catapult Load Index = sum(load)/sum(jumps)")
    parser.add_argument("--start", help="UTC start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", help="UTC end date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--json-out",
        default=os.getenv("LOAD_INDEX_JSON_OUT", "load_index_result.json"),
        help="Write per-activity breakdown JSON",
    )
    parser.add_argument(
        "--max-activities",
        type=int,
        default=None,
        metavar="N",
        help="Only process first N activities in range (smoke test; omit for full run)",
    )
    args = parser.parse_args()

    start_s = args.start or os.getenv("CATAPULT_LOAD_INDEX_START", "").strip()
    end_s = args.end or os.getenv("CATAPULT_LOAD_INDEX_END", "").strip()
    if start_s and end_s:
        start_d = datetime.strptime(start_s, "%Y-%m-%d").date()
        end_d = datetime.strptime(end_s, "%Y-%m-%d").date()
    else:
        start_d, end_d = default_range()
        print(f"[INFO] Using default UTC window: {start_d} .. {end_d}")

    if end_d < start_d:
        print("[ERROR] end before start")
        return 1

    try:
        token = config.catapult_token()
        base = config.catapult_base_url()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    print(f"[INFO] Fetching activities...")
    activities = fetch_activities(headers, base)
    time.sleep(PAUSE_S)
    in_range = activities_in_range(activities, start_d, end_d)
    if args.max_activities is not None and args.max_activities > 0:
        in_range = in_range[: args.max_activities]
        print(f"[INFO] --max-activities {args.max_activities} applied")
    print(f"[INFO] {len(in_range)} activit(y/ies) in range (of {len(activities)} total)\n")

    total_load = 0.0
    total_jumps = 0
    breakdown: list[dict[str, Any]] = []

    for idx, act in enumerate(in_range):
        aid = act.get("id")
        name = act.get("name", "")
        if not aid:
            continue
        print(f"[{idx + 1}/{len(in_range)}] {name} ({aid})")

        load_sum = sum_player_load_for_activity(headers, base, aid)
        total_load += load_sum
        time.sleep(PAUSE_S)

        athletes = fetch_activity_athletes(headers, base, aid)
        time.sleep(PAUSE_S)
        act_jumps = 0
        for j, ath in enumerate(athletes):
            ath_id = ath.get("id")
            if not ath_id:
                continue
            nj = fetch_jump_count_for_athlete(headers, base, aid, ath_id)
            act_jumps += nj
            if (j + 1) % 10 == 0:
                print(f"    ... athletes {j + 1}/{len(athletes)}, jumps so far {act_jumps}")
            time.sleep(PAUSE_S)

        total_jumps += act_jumps
        breakdown.append(
            {
                "activity_id": aid,
                "activity_name": name,
                "sum_player_load": load_sum,
                "jump_count": act_jumps,
                "load_index_local": (load_sum / act_jumps) if act_jumps else None,
            }
        )
        print(f"    load_sum={load_sum:.4f}, jumps={act_jumps}\n")

    result = {
        "start_date": start_d.isoformat(),
        "end_date": end_d.isoformat(),
        "sum_player_load": total_load,
        "total_jump_count": total_jumps,
        "load_index": (total_load / total_jumps) if total_jumps else None,
        "activities": breakdown,
    }

    out_path = args.json_out
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("=" * 50)
    print(f"Sum of Player Load (total_player_load): {total_load:.6f}")
    print(f"Total jump count (jump_attribute > 0): {total_jumps}")
    if total_jumps:
        print(f"Load Index: {total_load / total_jumps:.6f}")
    else:
        print("Load Index: undefined (zero jumps in window)")
    print(f"[INFO] Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
