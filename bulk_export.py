import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("CATAPULT_TOKEN")
BASE_URL = "https://connect-au.catapultsports.com/api/v6"

def get_activities(limit=10):
    """Fetch a list of recent Activity IDs."""
    print(f"[INFO] Fetching the latest {limit} activities...")
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    
    response = requests.get(f"{BASE_URL}/activities", headers=headers)
    if response.status_code == 200:
        raw = response.json()
        # API may return a list or { "data": [...] }
        activities = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not isinstance(activities, list):
            activities = []
        # Return just the IDs for the top 'limit' activities
        return [act.get("id") for act in activities[:limit] if act.get("id")]
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

def run_bulk_export():
    if not TOKEN:
        print("[ERROR] Missing token.")
        return

    # 1. Get the last 10 activities to test the loop (change to 50 or 100 later)
    activity_ids = get_activities(limit=100)
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
    run_bulk_export()