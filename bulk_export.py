import argparse
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("CATAPULT_TOKEN")
BASE_URL = os.getenv("CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6").rstrip("/")

# Default cap on how many activity IDs to process (after GET /activities). Set env to 0 or use --all for no cap.
_DEFAULT_LIMIT_RAW = os.getenv("CATAPULT_BULK_EXPORT_LIMIT", "100").strip()


def _default_activity_limit() -> int | None:
    if not _DEFAULT_LIMIT_RAW or _DEFAULT_LIMIT_RAW == "0":
        return None
    try:
        n = int(_DEFAULT_LIMIT_RAW)
        return None if n <= 0 else n
    except ValueError:
        return 100


def get_activities(limit: int | None = 100) -> list:
    """Fetch activity IDs from GET /activities.

    ``limit`` truncates the list client-side (newest/first N depends on API order).
    ``limit`` None = use every activity returned in this response.

    Note: Catapult may cap how many sessions one GET returns; this script does not paginate.
    If you need more than one page, check Catapult API docs for query parameters or support.
    """
    if limit is None:
        print("[INFO] Fetching activities (no client-side limit; using full API response list)...")
    else:
        print(f"[INFO] Fetching activities (client cap: latest {limit})...")
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

    response = requests.get(f"{BASE_URL}/activities", headers=headers, timeout=120)
    if response.status_code == 200:
        raw = response.json()
        # API may return a list or { "data": [...] }
        activities = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not isinstance(activities, list):
            activities = []
        ids = [act.get("id") for act in activities if act.get("id")]
        if limit is not None and limit > 0:
            ids = ids[:limit]
        print(f"[INFO] Using {len(ids)} activity id(s) from GET /activities (response had {len(activities)} session(s)).")
        return ids
    else:
        print(f"[ERROR] Failed to fetch activities: {response.status_code}")
        return []

def get_stats_for_activity(activity_id):
    """Use the POST method to get stats for a specific activity."""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # The POST payload you successfully reverse-engineered
    payload = {
        "group_by": ["participating_athlete"],
        "filters": [
            {
                "name": "activity_id",
                "comparison": "=",
                "values": [activity_id]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/stats", headers=headers, json=payload)
    
    if response.status_code == 200:
        raw = response.json()
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get("data", [])
        return []
    else:
        print(f"  -> [WARNING] Failed to fetch stats for {activity_id}. HTTP {response.status_code}")
        return []

def run_bulk_export(limit: int | None) -> None:
    """``limit`` = max activities (client-side), or ``None`` = no cap (use full GET /activities list)."""
    if not TOKEN:
        print("[ERROR] Missing token.")
        return

    # 1. Activity IDs from GET /activities (see get_activities docstring for API limits)
    activity_ids = get_activities(limit=limit)
    if not activity_ids:
        return
        
    all_stats = []
    
    print(f"[INFO] Starting data extraction for {len(activity_ids)} sessions...\n")
    
    # 2. Loop through each ID and fetch the stats
    for index, act_id in enumerate(activity_ids):
        print(f"Processing {index + 1}/{len(activity_ids)}: Activity {act_id}...")
        
        stats = get_stats_for_activity(act_id)
        if stats:
            # Add the activity ID to each row so we know where the data came from
            for row in stats:
                row['source_activity_id'] = act_id
            all_stats.extend(stats)
            
        # RATE LIMITING: Pause for 1 second so Catapult doesn't block us
        time.sleep(1) 

    # 3. Save everything to a massive JSON file for Mingye
    output_filename = "catapult_bulk_export.json"
    with open(output_filename, "w") as f:
        json.dump(all_stats, f, indent=4)
        
    print(f"\n[SUCCESS] Extraction complete! Saved {len(all_stats)} individual athlete performance records to {output_filename}.")
    print("[NEXT STEP] Send this file to Mingye so he can begin modeling.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export Catapult POST /stats rows to catapult_bulk_export.json",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every activity returned by GET /activities (no client-side cap).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N activities (overrides --all). Default: CATAPULT_BULK_EXPORT_LIMIT env or 100.",
    )
    args = parser.parse_args()

    lim: int | None
    if args.all:
        lim = None
    elif args.limit is not None:
        lim = None if args.limit <= 0 else args.limit
    else:
        lim = _default_activity_limit()

    run_bulk_export(limit=lim)