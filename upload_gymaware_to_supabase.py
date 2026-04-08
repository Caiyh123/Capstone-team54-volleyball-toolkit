"""
Load gymaware_summaries_export.json into public.gymaware_summaries (upsert by reference).

Prerequisites:
  1. Run schema/gymaware_summaries.sql in Supabase SQL editor.
  2. python gymaware_export.py
  3. DATABASE_URL in .env

Run: python upload_gymaware_to_supabase.py
"""
from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
FILE_PATH = os.getenv("GYMAWARE_EXPORT_FILE", "gymaware_summaries_export.json")


def _num(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Any:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def map_row(row: dict[str, Any]) -> dict[str, Any]:
    ref = row.get("reference")
    if not ref:
        return {}
    targets = row.get("targets")
    return {
        "gymaware_reference": str(ref),
        "recorded": _num(row.get("recorded")),
        "modified": _num(row.get("modified")),
        "athlete_reference": row.get("athleteReference"),
        "athlete_name": row.get("athleteName"),
        "athlete_weight": _num(row.get("athleteWeight")),
        "exercise_name": row.get("exerciseName"),
        "bar_weight": _num(row.get("barWeight")),
        "rep_count": _int(row.get("repCount")),
        "targets": Json(targets) if isinstance(targets, dict) else None,
        "height": _num(row.get("height")),
        "dip": _num(row.get("dip")),
        "mean_velocity": _num(row.get("meanVelocity")),
        "peak_velocity": _num(row.get("peakVelocity")),
        "mean_power": _num(row.get("meanPower")),
        "peak_power": _num(row.get("peakPower")),
        "mean_watts_per_kg": _num(row.get("meanWattsPerKg")),
        "peak_watts_per_kg": _num(row.get("peakWattsPerKg")),
        "velocity_zone": row.get("velocityZone"),
        "activity_name": row.get("activityName"),
        "activity_reference": row.get("activityReference"),
        "raw": Json(row),
    }


UPSERT_SQL = """
INSERT INTO public.gymaware_summaries (
    gymaware_reference, recorded, modified, athlete_reference, athlete_name,
    athlete_weight, exercise_name, bar_weight, rep_count, targets,
    height, dip, mean_velocity, peak_velocity, mean_power, peak_power,
    mean_watts_per_kg, peak_watts_per_kg, velocity_zone, activity_name,
    activity_reference, raw, updated_at
) VALUES (
    %(gymaware_reference)s, %(recorded)s, %(modified)s, %(athlete_reference)s, %(athlete_name)s,
    %(athlete_weight)s, %(exercise_name)s, %(bar_weight)s, %(rep_count)s, %(targets)s,
    %(height)s, %(dip)s, %(mean_velocity)s, %(peak_velocity)s, %(mean_power)s, %(peak_power)s,
    %(mean_watts_per_kg)s, %(peak_watts_per_kg)s, %(velocity_zone)s, %(activity_name)s,
    %(activity_reference)s, %(raw)s, NOW()
)
ON CONFLICT (gymaware_reference) DO UPDATE SET
    recorded = EXCLUDED.recorded,
    modified = EXCLUDED.modified,
    athlete_reference = EXCLUDED.athlete_reference,
    athlete_name = EXCLUDED.athlete_name,
    athlete_weight = EXCLUDED.athlete_weight,
    exercise_name = EXCLUDED.exercise_name,
    bar_weight = EXCLUDED.bar_weight,
    rep_count = EXCLUDED.rep_count,
    targets = EXCLUDED.targets,
    height = EXCLUDED.height,
    dip = EXCLUDED.dip,
    mean_velocity = EXCLUDED.mean_velocity,
    peak_velocity = EXCLUDED.peak_velocity,
    mean_power = EXCLUDED.mean_power,
    peak_power = EXCLUDED.peak_power,
    mean_watts_per_kg = EXCLUDED.mean_watts_per_kg,
    peak_watts_per_kg = EXCLUDED.peak_watts_per_kg,
    velocity_zone = EXCLUDED.velocity_zone,
    activity_name = EXCLUDED.activity_name,
    activity_reference = EXCLUDED.activity_reference,
    raw = EXCLUDED.raw,
    updated_at = NOW()
"""


def main() -> None:
    if not DB_URL:
        print("[ERROR] DATABASE_URL not found in .env")
        return

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Missing {FILE_PATH}. Run: python gymaware_export.py")
        return

    if not isinstance(data, list):
        print("[ERROR] Export file must be a JSON array of objects.")
        return

    print(f"[INFO] Loaded {len(data)} row(s) from {FILE_PATH}")

    ok = 0
    skipped = 0
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        for row in data:
            if not isinstance(row, dict):
                skipped += 1
                continue
            mapped = map_row(row)
            if not mapped:
                skipped += 1
                continue
            try:
                cur.execute(UPSERT_SQL, mapped)
                ok += 1
            except Exception as e:
                print(f"  [WARNING] skip ref={row.get('reference')}: {e}")
                skipped += 1
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        return

    print(f"\n[SUCCESS] Upserted {ok} row(s); skipped {skipped}.")
    print("[CHECK] Supabase → Table Editor → gymaware_summaries, or run:")
    print("        SELECT COUNT(*) FROM public.gymaware_summaries;")


if __name__ == "__main__":
    main()
