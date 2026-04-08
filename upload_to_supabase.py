import os
import json
import psycopg2
from dotenv import load_dotenv

# 1. Load the secure database URL
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def upload_data():
    if not DB_URL:
        print("[ERROR] DATABASE_URL not found in your .env file.")
        return

    # 2. Open the JSON file you generated earlier
    file_path = "catapult_bulk_export.json"
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            print(f"[INFO] Successfully loaded {len(data)} records from {file_path}")
    except FileNotFoundError:
        print(f"[ERROR] Could not find {file_path}. Did you run the bulk_export.py script?")
        return

    # 3. Connect to the Supabase Cloud
    print("[INFO] Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        # Enable autocommit so if one row fails, it doesn't crash the whole batch
        conn.autocommit = True 
        cursor = conn.cursor()

        print("[INFO] Pushing data to the cloud...")
        success_count = 0

        # 4. Loop through the JSON and insert each row into the database
        for row in data:
            # Extract fields safely (defaulting to 0.0 if a metric is missing)
            activity_id = row.get("source_activity_id")
            
            # Handling nested athlete IDs depending on how Catapult formatted your specific export
            athlete_id = row.get("athlete_id") or row.get("participating_athlete", {}).get("id")
            
            total_distance = row.get("total_distance", 0.0)
            total_player_load = row.get("total_player_load", 0.0)
            field_time = row.get("field_time", 0.0)

            # Skip rows that are completely empty
            if not activity_id:
                continue

            # The SQL Insert Command
            insert_query = """
                INSERT INTO catapult_session_metrics 
                (activity_id, athlete_id, total_distance, total_player_load, field_time)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            try:
                cursor.execute(insert_query, (activity_id, athlete_id, total_distance, total_player_load, field_time))
                success_count += 1
            except Exception as row_error:
                print(f"  -> [WARNING] Skipped a row due to a data mismatch: {row_error}")
                continue

        print(f"\n[SUCCESS] Pipeline Complete! Uploaded {success_count} records to Supabase.")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Could not connect to the database. Details: {e}")

if __name__ == "__main__":
    upload_data()