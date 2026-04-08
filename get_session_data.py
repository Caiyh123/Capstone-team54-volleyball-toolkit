import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("CATAPULT_TOKEN")
BASE_URL = os.getenv("CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6")

# Paste an Activity ID here, or set ACTIVITY_ID in .env
ACTIVITY_ID = os.getenv("ACTIVITY_ID", "83a45bab-141d-4d90-a247-77b4b335c818")


def fetch_metrics():
    if not TOKEN:
        print("[ERROR] CATAPULT_TOKEN missing in .env")
        return

    if not ACTIVITY_ID or ACTIVITY_ID == "PASTE_ID_HERE":
        print("[ERROR] Set ACTIVITY_ID in this script or in .env")
        return

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # v6: stats are queried via POST /stats (not GET /stats?...).
    # group_by must be an array; filters need name, comparison (=, <>, >, ...), values.
    body = {
        "group_by": ["participating_athlete"],
        "filters": [
            {
                "name": "activity_id",
                "comparison": "=",
                "values": [ACTIVITY_ID],
            }
        ],
    }

    endpoint = f"{BASE_URL.rstrip('/')}/stats"
    print(f"[INFO] Fetching physical metrics for Activity ID: {ACTIVITY_ID}...")

    try:
        response = requests.post(endpoint, headers=headers, json=body, timeout=120)

        if response.status_code == 200:
            data = response.json()
            stats_list = data if isinstance(data, list) else data.get("data", [])

            print(f"[SUCCESS] Pulled {len(stats_list)} metric record(s) for this session!")
            print("-" * 50)

            if len(stats_list) > 0:
                print("[SCHEMA PREVIEW] Sample row (first record):")
                first = stats_list[0]
                if isinstance(first, dict):
                    for key, value in list(first.items())[:20]:
                        print(f"  -> {key}: {value}")
                    if len(first) > 20:
                        print(f"  ... ({len(first) - 20} more keys)")
                else:
                    print(f"  {first}")
            else:
                print(
                    "[INFO] No stats rows returned. Try group_by ['activity'] or another activity ID."
                )

            print("-" * 50)

        elif response.status_code == 404:
            print(f"[ERROR] 404 Not Found: {endpoint}")
        elif response.status_code == 422:
            print(
                "[ERROR] 422 Validation error. Check POST body (group_by, filters).",
            )
            try:
                print(json.dumps(response.json(), indent=2)[:800])
            except Exception:
                print(response.text[:500])
        else:
            print(f"[FAILED] HTTP {response.status_code}: {response.text[:500]}")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] {str(e)}")


if __name__ == "__main__":
    fetch_metrics()
