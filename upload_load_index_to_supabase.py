# Insert load_index_result.json into public.catapult_load_index_* (run with Python, not in SQL editor).
#   python load_index.py --start 2026-04-01 --end 2026-04-14
#   python upload_load_index_to_supabase.py [path/to/custom.json]
# Requires DATABASE_URL in .env. Apply schema/catapult_load_index.sql in Supabase first.
from __future__ import annotations

import json
import os
import sys
import uuid

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not set in .env", file=sys.stderr)
        return 1

    path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("LOAD_INDEX_JSON_OUT", "load_index_result.json")
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    activities = data.get("activities")
    if not isinstance(activities, list):
        print("[ERROR] JSON missing 'activities' array", file=sys.stderr)
        return 1

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.catapult_load_index_run (
                start_date, end_date, sum_player_load, total_jump_count, load_index
            )
            VALUES (%s::date, %s::date, %s, %s, %s)
            RETURNING id
            """,
            (
                data["start_date"],
                data["end_date"],
                float(data["sum_player_load"]),
                int(data["total_jump_count"]),
                None if data.get("load_index") is None else float(data["load_index"]),
            ),
        )
        row = cur.fetchone()
        if not row:
            print("[ERROR] INSERT run returned no id", file=sys.stderr)
            return 1
        # psycopg2 may not adapt Python uuid.UUID in all builds; use strings for parameters.
        run_id = str(row[0])

        for a in activities:
            if not isinstance(a, dict):
                continue
            aid = a.get("activity_id")
            if not aid:
                continue
            try:
                au = str(uuid.UUID(str(aid)))
            except (ValueError, TypeError):
                continue
            cur.execute(
                """
                INSERT INTO public.catapult_load_index_activity (
                    run_id, activity_id, activity_name,
                    sum_player_load, jump_count, load_index_local
                )
                VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    au,
                    a.get("activity_name"),
                    float(a.get("sum_player_load") or 0),
                    int(a.get("jump_count") or 0),
                    None
                    if a.get("load_index_local") is None
                    else float(a["load_index_local"]),
                ),
            )

        print(f"[SUCCESS] Inserted load index run id={run_id} with {len(activities)} activity row(s).")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
