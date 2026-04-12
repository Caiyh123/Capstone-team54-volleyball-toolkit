import json
import os
import sys
import uuid

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

from integrations.catapult.stats_row import activity_id_from_stats_row, athlete_id_from_stats_row

# 1. Load the secure database URL
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

UPSERT_STATS_SQL = """
INSERT INTO public.catapult_stats_staging (activity_id, athlete_id, stats_payload, synced_at)
VALUES (%(activity_id)s::uuid, %(athlete_id)s::uuid, %(stats_payload)s, NOW())
ON CONFLICT ON CONSTRAINT catapult_stats_staging_pkey DO UPDATE SET
    stats_payload = EXCLUDED.stats_payload,
    athlete_id = EXCLUDED.athlete_id,
    synced_at = NOW()
"""


def _parse_uuid(s: str | None):
    if not s:
        return None
    try:
        return uuid.UUID(str(s))
    except (ValueError, TypeError):
        return None


def upload_data() -> int:
    if not DB_URL:
        print("[ERROR] DATABASE_URL not found in your .env file.")
        return 1

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
                    UPSERT_STATS_SQL,
                    {
                        "activity_id": aid_uuid,
                        "athlete_id": ath_uuid,
                        "stats_payload": Json(row),
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
                print(f"  -> [WARNING] JSONB upsert skipped: {e}")
                jsonb_skip += 1

            # --- Legacy narrow columns (backward compatible)
            insert_query = """
                INSERT INTO catapult_session_metrics
                (activity_id, athlete_id, total_distance, total_player_load, field_time)
                VALUES (%s, %s, %s, %s, %s)
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

        print(f"\n[SUCCESS] catapult_stats_staging upserted: {jsonb_ok} row(s); skipped: {jsonb_skip}.")
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
