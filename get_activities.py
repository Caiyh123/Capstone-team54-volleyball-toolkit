import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("CATAPULT_TOKEN")
BASE_URL = "https://connect-au.catapultsports.com/api/v6"

def fetch_recent_activities():
    if not TOKEN:
        print("[ERROR] Token missing.")
        return

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    }
    
    # The endpoint to get training sessions/matches
    endpoint = f"{BASE_URL}/activities"
    
    print("[INFO] Fetching recent activities (sessions) from Catapult...")

    try:
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            activities = response.json()
            
            # Catapult sometimes returns a list directly, or wraps it in a dictionary (like {'data': [...]})
            # We'll handle both just in case.
            activity_list = activities.get('data', activities) if isinstance(activities, dict) else activities
            
            print(f"[SUCCESS] Found {len(activity_list)} activities!")
            print("-" * 50)
            
            # Print the top 3 most recent activities so you can see the data structure
            for i, act in enumerate(activity_list[:3]):
                act_id = act.get('id', 'Unknown ID')
                name = act.get('name', 'Unnamed Session')
                start_time = act.get('start_time', 'Unknown Time')
                print(f"{i+1}. Activity ID: {act_id} | Name: {name} | Date: {start_time}")
            
            print("-" * 50)
            print("[NEXT STEP] Copy one of those Activity IDs. We will use it to pull the physical load metrics.")
            
        else:
            print(f"[FAILED] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    fetch_recent_activities()