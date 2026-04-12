"""
Introspect Catapult Connect v6: summary stats (POST /stats) vs 10 Hz sensor (GET .../sensor).

Requires CATAPULT_TOKEN and optional CATAPULT_BASE_URL in .env.

Does not download full sensor payloads by default (can be multi-MB per athlete).
Run from repo root: python scripts/catapult_discover.py

Writes optional JSON summary to catapult_api_discovery.json when --write-json is set.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Catapult API summary vs sensor discovery")
    parser.add_argument(
        "--activity-index",
        type=int,
        default=0,
        help="Which activity to sample from GET /activities (default 0)",
    )
    parser.add_argument(
        "--athlete-index",
        type=int,
        default=0,
        help="Which athlete from GET /activities/{id}/athletes (default 0)",
    )
    parser.add_argument(
        "--sensor-sample-rows",
        type=int,
        default=3,
        help="Number of 10 Hz rows to include in report (default 3; full pull is huge)",
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        help="Write catapult_api_discovery.json to cwd",
    )
    parser.add_argument(
        "--include-sensor",
        action="store_true",
        help="Download GET .../sensor (can be multi-MB per athlete; default is stats only)",
    )
    args = parser.parse_args()

    token = os.getenv("CATAPULT_TOKEN", "").strip()
    base = os.getenv("CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6").rstrip("/")
    if not token:
        print("[ERROR] CATAPULT_TOKEN missing.", file=sys.stderr)
        return 1

    h = _headers(token)
    out: dict[str, Any] = {
        "api_base": base,
        "summary": {},
        "sensor": {},
    }

    # Activities
    r = requests.get(f"{base}/activities", headers=h, timeout=120)
    if r.status_code != 200:
        print(f"[ERROR] GET /activities HTTP {r.status_code}: {r.text[:400]}", file=sys.stderr)
        return 1
    raw = r.json()
    acts = raw.get("data", raw) if isinstance(raw, dict) else raw
    if not isinstance(acts, list) or not acts:
        print("[ERROR] No activities returned.", file=sys.stderr)
        return 1
    if args.activity_index >= len(acts):
        print("[ERROR] --activity-index out of range.", file=sys.stderr)
        return 1
    activity = acts[args.activity_index]
    activity_id = activity.get("id")
    out["sample_activity"] = {
        "id": activity_id,
        "name": activity.get("name"),
        "start_time": activity.get("start_time"),
        "keys": sorted(activity.keys()) if isinstance(activity, dict) else [],
    }

    # Stats row keys (summary data)
    body = {
        "group_by": ["participating_athlete"],
        "filters": [
            {"name": "activity_id", "comparison": "=", "values": [activity_id]},
        ],
    }
    rs = requests.post(f"{base}/stats", headers=h, json=body, timeout=120)
    if rs.status_code != 200:
        print(f"[ERROR] POST /stats HTTP {rs.status_code}: {rs.text[:400]}", file=sys.stderr)
        return 1
    sraw = rs.json()
    rows = sraw if isinstance(sraw, list) else sraw.get("data", []) if isinstance(sraw, dict) else []
    out["summary"] = {
        "endpoint": "POST /stats",
        "group_by_used": ["participating_athlete"],
        "rows_returned": len(rows),
        "metric_keys_per_row": sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
        "metric_key_count": len(rows[0].keys()) if rows and isinstance(rows[0], dict) else 0,
        "note": "Current upload_to_supabase.py only persists total_distance, total_player_load, field_time plus ids.",
    }

    # Athletes in activity (for optional 10 Hz sample)
    ra = requests.get(f"{base}/activities/{activity_id}/athletes", headers=h, timeout=120)
    if not args.include_sensor:
        out["sensor"] = {
            "skipped": True,
            "endpoint": "GET /activities/{activity_id}/athletes/{athlete_id}/sensor",
            "note": "Re-run with --include-sensor to download 10 Hz (large). See docs/volley-etl/catapult_summary_and_sensor.md.",
        }
    elif ra.status_code != 200:
        print(f"[WARN] GET /activities/{{id}}/athletes HTTP {ra.status_code}", file=sys.stderr)
        out["sensor"]["error"] = "Could not list athletes for sensor sample."
    else:
        araw = ra.json()
        arows = araw if isinstance(araw, list) else araw.get("data", [])
        if not isinstance(arows, list) or not arows:
            out["sensor"]["error"] = "No athletes on this activity."
        elif args.athlete_index >= len(arows):
            print("[ERROR] --athlete-index out of range.", file=sys.stderr)
            return 1
        else:
            athlete_id = arows[args.athlete_index].get("id")
            url = f"{base}/activities/{activity_id}/athletes/{athlete_id}/sensor"
            # Full JSON can be very large; stream parse would be better for production
            rx = requests.get(url, headers=h, timeout=300)
            if rx.status_code != 200:
                out["sensor"] = {
                    "endpoint": "GET .../activities/{activity_id}/athletes/{athlete_id}/sensor",
                    "http_status": rx.status_code,
                    "error": rx.text[:500],
                }
            else:
                sensor_list = rx.json()
                if not isinstance(sensor_list, list) or not sensor_list:
                    out["sensor"] = {"error": "Empty sensor list"}
                else:
                    block = sensor_list[0]
                    data = block.get("data")
                    n = len(data) if isinstance(data, list) else 0
                    sample: list[dict[str, Any]] = []
                    if isinstance(data, list) and data:
                        for i in range(min(args.sensor_sample_rows, len(data))):
                            if isinstance(data[i], dict):
                                sample.append(data[i])
                    out["sensor"] = {
                        "endpoint": f"GET /activities/{{activity_id}}/athletes/{{athlete_id}}/sensor",
                        "resolved_url_pattern": url.split("?")[0],
                        "stream_type": block.get("stream_type"),
                        "device_id": block.get("device_id"),
                        "ten_hz_row_count": n,
                        "ten_hz_columns": sorted(data[0].keys()) if data and isinstance(data[0], dict) else [],
                        "sample_rows": sample,
                        "note": "Full response can be several MB per athlete. Store as files/TSDB or downsample for Postgres.",
                    }

    print(json.dumps(out, indent=2, default=str))
    if args.write_json:
        path = "catapult_api_discovery.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
            f.write("\n")
        print(f"\n[INFO] Wrote {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
