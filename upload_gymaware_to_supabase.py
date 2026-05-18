"""
Load GymAware export JSON files into Supabase staging + BI extract tables.

Files (from gymaware_export.py):
  gymaware_summaries_export.json
  gymaware_reps_export.json
  gymaware_athletes_export.json
  gymaware_bests_export.json

Prerequisites:
  schema/gymaware_summaries.sql, schema/gymaware_extended.sql,
  schema/medallion_raw_layer_migration.sql, DATABASE_URL in .env

Roster: ROSTER_FILTER=1 or GYMAWARE_USE_ALLOWLIST=1 filters all resources.

Run: python upload_gymaware_to_supabase.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_batch

from integrations.gymaware.allowlist import (
    env_use_allowlist,
    filter_rows_by_athlete_reference,
    load_athlete_references_from_xlsx,
)
from integrations.gymaware.bi_fields import (
    athlete_bi_fields,
    best_bi_fields,
    parse_bar_weight,
    rep_bi_fields,
    summary_bi_fields,
)

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
ROOT = Path(__file__).resolve().parent

SUMMARIES_FILE = os.getenv("GYMAWARE_EXPORT_FILE", "gymaware_summaries_export.json")
REPS_FILE = os.getenv("GYMAWARE_REPS_EXPORT_FILE", "gymaware_reps_export.json")
ATHLETES_FILE = os.getenv("GYMAWARE_ATHLETES_EXPORT_FILE", "gymaware_athletes_export.json")
BESTS_FILE = os.getenv("GYMAWARE_BESTS_EXPORT_FILE", "gymaware_bests_export.json")

INSERT_SUMMARY_STAGING = """
INSERT INTO public.gymaware_summaries (
    gymaware_reference, recorded, modified, athlete_reference, athlete_name,
    athlete_weight, exercise_name, bar_weight, rep_count, targets,
    height, dip, mean_velocity, peak_velocity, mean_power, peak_power,
    mean_watts_per_kg, peak_watts_per_kg, velocity_zone, activity_name,
    activity_reference, raw, updated_at, etl_ingested_at
) VALUES (
    %(gymaware_reference)s, %(recorded)s, %(modified)s, %(athlete_reference)s, %(athlete_name)s,
    %(athlete_weight)s, %(exercise_name)s, %(bar_weight)s, %(rep_count)s, %(targets)s,
    %(height)s, %(dip)s, %(mean_velocity)s, %(peak_velocity)s, %(mean_power)s, %(peak_power)s,
    %(mean_watts_per_kg)s, %(peak_watts_per_kg)s, %(velocity_zone)s, %(activity_name)s,
    %(activity_reference)s, %(raw)s, NOW(), NOW()
)
RETURNING id
"""

INSERT_SUMMARY_BI = """
INSERT INTO public.gymaware_summaries_bi_extract (
    source_staging_id, gymaware_reference, recorded, modified, athlete_reference, athlete_name,
    athlete_weight, exercise_name, exercise_reference, bar_weight, rep_count,
    height, dip, mean_velocity, peak_velocity, mean_power, peak_power,
    mean_watts_per_kg, peak_watts_per_kg, velocity_zone, activity_name, activity_reference,
    sensor, hardware, notes, deleted, targets_mode, targets_analysis,
    targets_best_max, targets_best_min, targets_last_max, targets_last_min,
    targets_squad_max, targets_squad_min, targets_preset_max, targets_preset_min,
    vendor_synced_at, etl_ingested_at
) VALUES (
    %(source_staging_id)s, %(gymaware_reference)s, %(recorded)s, %(modified)s,
    %(athlete_reference)s, %(athlete_name)s, %(athlete_weight)s, %(exercise_name)s,
    %(exercise_reference)s, %(bar_weight)s, %(rep_count)s, %(height)s, %(dip)s,
    %(mean_velocity)s, %(peak_velocity)s, %(mean_power)s, %(peak_power)s,
    %(mean_watts_per_kg)s, %(peak_watts_per_kg)s, %(velocity_zone)s, %(activity_name)s,
    %(activity_reference)s, %(sensor)s, %(hardware)s, %(notes)s, %(deleted)s,
    %(targets_mode)s, %(targets_analysis)s, %(targets_best_max)s, %(targets_best_min)s,
    %(targets_last_max)s, %(targets_last_min)s, %(targets_squad_max)s, %(targets_squad_min)s,
    %(targets_preset_max)s, %(targets_preset_min)s, %(vendor_synced_at)s, NOW()
)
"""

INSERT_REPS_STAGING = """
INSERT INTO public.gymaware_reps_staging (
    set_reference, athlete_reference, payload, synced_at, etl_ingested_at
) VALUES (
    %(set_reference)s, %(athlete_reference)s, %(payload)s, NOW(), NOW()
)
RETURNING ingest_id
"""

INSERT_REP_BI = """
INSERT INTO public.gymaware_rep_bi_extract (
    source_staging_ingest_id, set_reference, rep_num, recorded, modified,
    athlete_reference, athlete_name, athlete_weight, exercise_name, exercise_reference,
    bar_weight, rep_count, activity_name, activity_reference, rep_metrics,
    vendor_synced_at, etl_ingested_at
) VALUES (
    %(source_staging_ingest_id)s, %(set_reference)s, %(rep_num)s, %(recorded)s, %(modified)s,
    %(athlete_reference)s, %(athlete_name)s, %(athlete_weight)s, %(exercise_name)s,
    %(exercise_reference)s, %(bar_weight)s, %(rep_count)s, %(activity_name)s,
    %(activity_reference)s, %(rep_metrics)s, %(vendor_synced_at)s, NOW()
)
"""

INSERT_ATHLETE_STAGING = """
INSERT INTO public.gymaware_athletes_staging (
    athlete_reference, payload, synced_at, etl_ingested_at
) VALUES (%(athlete_reference)s, %(payload)s, NOW(), NOW())
RETURNING ingest_id
"""

INSERT_ATHLETE_BI = """
INSERT INTO public.gymaware_athletes_bi_extract (
    source_staging_ingest_id, athlete_reference, display_name, first_name, last_name,
    jersey_number, position, sport, address, phone, born, photo, modified,
    vendor_synced_at, etl_ingested_at
) VALUES (
    %(source_staging_ingest_id)s, %(athlete_reference)s, %(display_name)s, %(first_name)s,
    %(last_name)s, %(jersey_number)s, %(position)s, %(sport)s, %(address)s, %(phone)s,
    %(born)s, %(photo)s, %(modified)s, %(vendor_synced_at)s, NOW()
)
"""

INSERT_BESTS_STAGING = """
INSERT INTO public.gymaware_bests_staging (
    athlete_reference, exercise_name, bar_weight, payload, synced_at, etl_ingested_at
) VALUES (
    %(athlete_reference)s, %(exercise_name)s, %(bar_weight)s, %(payload)s, NOW(), NOW()
)
RETURNING ingest_id
"""

INSERT_BESTS_BI = """
INSERT INTO public.gymaware_bests_bi_extract (
    source_staging_ingest_id, athlete_reference, athlete_name, exercise_name, bar_weight,
    height, dip, mean_velocity, peak_velocity, mean_power, peak_power,
    mean_watts_per_kg, peak_watts_per_kg, vendor_synced_at, etl_ingested_at
) VALUES (
    %(source_staging_ingest_id)s, %(athlete_reference)s, %(athlete_name)s, %(exercise_name)s,
    %(bar_weight)s, %(height)s, %(dip)s, %(mean_velocity)s, %(peak_velocity)s,
    %(mean_power)s, %(peak_power)s, %(mean_watts_per_kg)s, %(peak_watts_per_kg)s,
    %(vendor_synced_at)s, NOW()
)
"""


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a JSON array")
    return [r for r in data if isinstance(r, dict)]


def _map_summary_staging(row: dict[str, Any]) -> dict[str, Any] | None:
    ref = row.get("reference")
    if not ref:
        return None
    targets = row.get("targets")
    return {
        "gymaware_reference": str(ref),
        "recorded": row.get("recorded"),
        "modified": row.get("modified"),
        "athlete_reference": str(row["athleteReference"])
        if row.get("athleteReference") is not None
        else None,
        "athlete_name": row.get("athleteName"),
        "athlete_weight": row.get("athleteWeight"),
        "exercise_name": row.get("exerciseName"),
        "bar_weight": row.get("barWeight"),
        "rep_count": row.get("repCount"),
        "targets": Json(targets) if isinstance(targets, dict) else None,
        "height": row.get("height"),
        "dip": row.get("dip"),
        "mean_velocity": row.get("meanVelocity"),
        "peak_velocity": row.get("peakVelocity"),
        "mean_power": row.get("meanPower"),
        "peak_power": row.get("peakPower"),
        "mean_watts_per_kg": row.get("meanWattsPerKg"),
        "peak_watts_per_kg": row.get("peakWattsPerKg"),
        "velocity_zone": row.get("velocityZone"),
        "activity_name": row.get("activityName"),
        "activity_reference": row.get("activityReference"),
        "raw": Json(row),
    }


def upload_summaries(
    cur: Any, rows: list[dict[str, Any]], *, bi_warned: list[bool]
) -> tuple[int, int, int]:
    staging_ok = bi_ok = skip = 0
    for row in rows:
        mapped = _map_summary_staging(row)
        if not mapped:
            skip += 1
            continue
        try:
            cur.execute(INSERT_SUMMARY_STAGING, mapped)
            ret = cur.fetchone()
            staging_id = int(ret[0]) if ret else None
            staging_ok += 1
        except Exception as e:
            print(f"  [WARN] summary staging skip ref={row.get('reference')}: {e}")
            skip += 1
            continue
        if staging_id is None:
            continue
        bi = summary_bi_fields(row)
        bi["source_staging_id"] = staging_id
        bi["vendor_synced_at"] = None
        try:
            cur.execute(INSERT_SUMMARY_BI, bi)
            bi_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_summaries_bi_extract failed. Apply schema/gymaware_extended.sql. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
    return staging_ok, bi_ok, skip


def upload_reps(cur: Any, rows: list[dict[str, Any]], *, bi_warned: list[bool]) -> tuple[int, int, int]:
    staging_ok = rep_rows = skip = 0
    for row in rows:
        ref = row.get("reference")
        if not ref:
            skip += 1
            continue
        ar = row.get("athleteReference")
        try:
            cur.execute(
                INSERT_REPS_STAGING,
                {
                    "set_reference": str(ref),
                    "athlete_reference": str(ar) if ar is not None else None,
                    "payload": Json(row),
                },
            )
            ret = cur.fetchone()
            ingest_id = int(ret[0]) if ret else None
            staging_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_reps_staging failed. Apply schema/gymaware_extended.sql. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
            skip += 1
            continue
        reps = row.get("reps")
        if ingest_id is None or not isinstance(reps, list):
            continue
        batch: list[dict[str, Any]] = []
        for i, rep in enumerate(reps, start=1):
            if not isinstance(rep, dict):
                continue
            fields = rep_bi_fields(row, rep, i)
            fields["source_staging_ingest_id"] = ingest_id
            fields["rep_metrics"] = Json(fields.pop("rep_metrics"))
            fields["vendor_synced_at"] = None
            batch.append(fields)
        if batch:
            try:
                execute_batch(cur, INSERT_REP_BI, batch, page_size=200)
                rep_rows += len(batch)
            except Exception as e:
                if not bi_warned[0]:
                    print(
                        "[WARN] gymaware_rep_bi_extract failed. "
                        f"First error: {e}",
                        file=sys.stderr,
                    )
                    bi_warned[0] = True
    return staging_ok, rep_rows, skip


def upload_athletes(
    cur: Any, rows: list[dict[str, Any]], *, bi_warned: list[bool]
) -> tuple[int, int, int]:
    staging_ok = bi_ok = skip = 0
    for row in rows:
        ar = row.get("athleteReference")
        if ar is None:
            skip += 1
            continue
        try:
            cur.execute(
                INSERT_ATHLETE_STAGING,
                {
                    "athlete_reference": str(ar),
                    "payload": Json(row),
                },
            )
            ret = cur.fetchone()
            ingest_id = int(ret[0]) if ret else None
            staging_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_athletes_staging failed. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
            skip += 1
            continue
        if ingest_id is None:
            continue
        bi = athlete_bi_fields(row)
        bi["source_staging_ingest_id"] = ingest_id
        bi["vendor_synced_at"] = None
        try:
            cur.execute(INSERT_ATHLETE_BI, bi)
            bi_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_athletes_bi_extract failed. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
    return staging_ok, bi_ok, skip


def upload_bests(cur: Any, rows: list[dict[str, Any]], *, bi_warned: list[bool]) -> tuple[int, int, int]:
    staging_ok = bi_ok = skip = 0
    for row in rows:
        try:
            cur.execute(
                INSERT_BESTS_STAGING,
                {
                    "athlete_reference": str(row["athleteReference"])
                    if row.get("athleteReference") is not None
                    else None,
                    "exercise_name": row.get("exerciseName"),
                    "bar_weight": parse_bar_weight(row.get("barWeight")),
                    "payload": Json(row),
                },
            )
            ret = cur.fetchone()
            ingest_id = int(ret[0]) if ret else None
            staging_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_bests_staging failed. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
            skip += 1
            continue
        if ingest_id is None:
            continue
        bi = best_bi_fields(row)
        bi["source_staging_ingest_id"] = ingest_id
        bi["vendor_synced_at"] = None
        try:
            cur.execute(INSERT_BESTS_BI, bi)
            bi_ok += 1
        except Exception as e:
            if not bi_warned[0]:
                print(
                    "[WARN] gymaware_bests_bi_extract failed. "
                    f"First error: {e}",
                    file=sys.stderr,
                )
                bi_warned[0] = True
    return staging_ok, bi_ok, skip


def main() -> int:
    if not DB_URL:
        print("[ERROR] DATABASE_URL not found in .env", file=sys.stderr)
        return 1

    allow_refs: set[int] | None = None
    if env_use_allowlist():
        try:
            _, allow_refs = load_athlete_references_from_xlsx()
        except FileNotFoundError as e:
            print(f"[ERROR] ROSTER_FILTER=1 but roster workbook missing: {e}", file=sys.stderr)
            return 1
        if not allow_refs:
            print("[ERROR] Roster filter enabled but workbook has no GymAware IDs.", file=sys.stderr)
            return 1
        print(f"[INFO] ROSTER_FILTER: upload limited to {len(allow_refs)} athlete reference(s).")

    try:
        summaries = _load_json(ROOT / SUMMARIES_FILE)
        reps = _load_json(ROOT / REPS_FILE)
        athletes = _load_json(ROOT / ATHLETES_FILE)
        bests = _load_json(ROOT / BESTS_FILE)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if allow_refs is not None:
        summaries = filter_rows_by_athlete_reference(summaries, allow_refs)
        reps = filter_rows_by_athlete_reference(reps, allow_refs)
        bests = filter_rows_by_athlete_reference(bests, allow_refs)
        filtered_athletes: list[dict[str, Any]] = []
        for a in athletes:
            try:
                ar_int = int(a.get("athleteReference"))
            except (TypeError, ValueError):
                continue
            if ar_int in allow_refs:
                filtered_athletes.append(a)
        athletes = filtered_athletes

    print(
        f"[INFO] Loaded rows — summaries: {len(summaries)}, reps sets: {len(reps)}, "
        f"athletes: {len(athletes)}, bests: {len(bests)}"
    )

    bi_warned = [False]
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        s_stg, s_bi, s_skip = upload_summaries(cur, summaries, bi_warned=bi_warned)
        r_stg, r_rep, r_skip = upload_reps(cur, reps, bi_warned=bi_warned)
        a_stg, a_bi, a_skip = upload_athletes(cur, athletes, bi_warned=bi_warned)
        b_stg, b_bi, b_skip = upload_bests(cur, bests, bi_warned=bi_warned)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database error: {e}", file=sys.stderr)
        return 1

    print(f"\n[SUCCESS] gymaware_summaries: {s_stg} staging, {s_bi} bi_extract, {s_skip} skipped.")
    print(f"[SUCCESS] gymaware_reps: {r_stg} sets staging, {r_rep} rep bi rows, {r_skip} skipped.")
    print(f"[SUCCESS] gymaware_athletes: {a_stg} staging, {a_bi} bi_extract, {a_skip} skipped.")
    print(f"[SUCCESS] gymaware_bests: {b_stg} staging, {b_bi} bi_extract, {b_skip} skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
