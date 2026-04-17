import json
import os
import sys
import uuid

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

from integrations.catapult.stats_row import (
    activity_id_from_stats_row,
    athlete_id_from_stats_row,
    athlete_jersey_from_stats_row,
)
from integrations.roster_allowlist import (
    catapult_roster_filters,
    env_roster_filter_enabled,
    load_roster_allowlist,
)

# 1. Load the secure database URL
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Medallion raw: append-only. Requires schema/medallion_raw_layer_migration.sql (ingest_id PK + etl_ingested_at).
INSERT_STATS_SQL = """
INSERT INTO public.catapult_stats_staging (activity_id, athlete_id, stats_payload, synced_at, etl_ingested_at)
VALUES (%(activity_id)s::uuid, %(athlete_id)s::uuid, %(stats_payload)s, NOW(), NOW())
"""


def _parse_uuid(s: str | None):
    if not s:
        return None
    try:
        return uuid.UUID(str(s))
    except (ValueError, TypeError):
        return None


def _stats_payload_jsonb(row: dict) -> Json:
    return Json(json.loads(json.dumps(row, default=str)))


def upload_data() -> int:
    if not DB_URL:
        print("[ERROR] DATABASE_URL not found in your .env file.")
        return 1

    allow_uuids: set[str] | None = None
    allow_jerseys_fold: set[str] | None = None
    if env_roster_filter_enabled():
        try:
            _, roster = load_roster_allowlist()
        except FileNotFoundError as e:
            print(f"[ERROR] ROSTER_FILTER=1 but roster workbook missing: {e}")
            return 1
        allow_uuids, allow_jerseys_fold = catapult_roster_filters(DB_URL, roster)
        if not allow_uuids and not allow_jerseys_fold:
            print(
                "[ERROR] ROSTER_FILTER=1 but no Catapult filter resolved. "
                "Add 'Catapult Jerseys' to the roster workbook, or catapult_athlete_id in athlete_identity."
            )
            return 1
        if allow_jerseys_fold is not None:
            print(
                f"[INFO] ROSTER_FILTER: Catapult upload restricted to {len(allow_jerseys_fold)} jersey code(s)."
            )
        else:
            print(f"[INFO] ROSTER_FILTER: Catapult upload restricted to {len(allow_uuids or [])} athlete UUID(s).")

    file_path = "catapult_bulk_export.json"
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            print(f"[INFO] Successfully loaded {len(data)} records from {file_path}")
    except FileNotFoundError:
        print(f"[ERROR] Could not find {file_path}. Did you run the bulk_export.py script?")
        return 1

    print("[INFO] Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("[INFO] Pushing data to the cloud...")
        narrow_ok = 0
        jsonb_ok = 0
        jsonb_skip = 0

        for row in data:
            if not isinstance(row, dict):
                continue

            activity_id = activity_id_from_stats_row(row)
            athlete_id_str = athlete_id_from_stats_row(row)

            if allow_jerseys_fold is not None:
                j = athlete_jersey_from_stats_row(row)
                if not j or j.casefold() not in allow_jerseys_fold:
                    continue
            elif allow_uuids is not None:
                if not athlete_id_str or str(athlete_id_str).strip().lower() not in allow_uuids:
                    continue

            total_distance = row.get("total_distance", 0.0)
            total_player_load = row.get("total_player_load", 0.0)
            field_time = row.get("field_time", 0.0)

            aid_uuid = _parse_uuid(activity_id)
            ath_uuid = _parse_uuid(athlete_id_str)

            if not aid_uuid:
                continue

            # --- Full JSONB stats (BI)
            try:
                cursor.execute(
                    INSERT_STATS_SQL,
                    {
                        "activity_id": str(aid_uuid),
                        "athlete_id": str(ath_uuid) if ath_uuid else None,
                        "stats_payload": _stats_payload_jsonb(row),
                    },
                )
                jsonb_ok += 1
            except Exception as e:
                if "catapult_stats_staging" in str(e) or "does not exist" in str(e).lower():
                    print(
                        "[ERROR] catapult_stats_staging missing. Apply schema/catapult_stats_staging.sql in Supabase.",
                        file=sys.stderr,
                    )
                    return 1
                print(f"  -> [WARNING] JSONB insert skipped: {e}")
                jsonb_skip += 1

            # --- Legacy narrow columns (backward compatible)
            insert_query = """
                INSERT INTO catapult_session_metrics
                (activity_id, athlete_id, total_distance, total_player_load, field_time, etl_ingested_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            try:
                cursor.execute(
                    insert_query,
                    (str(aid_uuid), str(ath_uuid) if ath_uuid else None, total_distance, total_player_load, field_time),
                )
                narrow_ok += 1
            except Exception as row_error:
                print(f"  -> [WARNING] Narrow insert skipped: {row_error}")
                continue

        print(f"\n[SUCCESS] catapult_stats_staging inserted: {jsonb_ok} row(s); skipped: {jsonb_skip}.")
        print(f"[SUCCESS] catapult_session_metrics inserted: {narrow_ok} row(s).")
        print("[CHECK] SELECT COUNT(*), MAX(synced_at) FROM public.catapult_stats_staging;")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Could not connect to the database. Details: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(upload_data())
