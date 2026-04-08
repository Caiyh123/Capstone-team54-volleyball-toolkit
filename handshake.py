import os
import requests
from dotenv import load_dotenv

# 1. Load the secret variables from your .env file
load_dotenv()

# 2. Retrieve your token
TOKEN = os.getenv("CATAPULT_TOKEN")

# 3. Catapult Connect v6 base URL (pick region: connect-au, connect-eu, connect-us, connect-cn)
BASE_URL = os.getenv("CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6")
# v6 has no /about; use /athletes as a simple connectivity + auth check
ENDPOINT = f"{BASE_URL.rstrip('/')}/athletes"

def run_handshake():
    # Security check: Ensure token is actually loaded
    if not TOKEN:
        print("[ERROR] No token found. Check if your .env file is named correctly.")
        return

    # Headers for the secure request
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    }

    print("[INFO] Initiating handshake with Catapult Cloud (AU Region, v6)...")

    try:
        # The 'GET' request
        response = requests.get(ENDPOINT, headers=headers)

        # Check the response status
        if response.status_code == 200:
            try:
                data = response.json()
                print("[SUCCESS] Handshake complete! Token is valid for Catapult Connect v6.")
                print("-" * 40)
                # Response is often a list or paged object; handle common shapes
                if isinstance(data, list):
                    print(f"Athletes returned: {len(data)}")
                    if data:
                        first = data[0]
                        if isinstance(first, dict):
                            fn = first.get("first_name") or first.get("firstName") or ""
                            ln = first.get("last_name") or first.get("lastName") or ""
                            name = (f"{fn} {ln}".strip() or first.get("name") or first.get("fullName") or first.get("id"))
                        else:
                            name = str(first)[:80]
                        print(f"First athlete (sample): {name}")
                elif isinstance(data, dict):
                    items = data.get("items") or data.get("data") or data.get("athletes")
                    if isinstance(items, list):
                        print(f"Athletes returned: {len(items)}")
                    else:
                        print(f"Response keys: {list(data.keys())[:10]}")
                print("-" * 40)
                print("[INFO] Your backend is ready for data ingestion.")
            except ValueError:
                print("[SUCCESS] Reached Catapult, but the response was not in JSON format.")
                print(f"Raw response: {response.text[:200]}...")

        elif response.status_code == 401:
            print("[ERROR] 401 Unauthorized. Double-check your token string in the .env file.")
        elif response.status_code == 403:
            print("[ERROR] 403 Forbidden. Token is valid, but lacks permission for this endpoint.")
        elif response.status_code == 404:
            print(f"[ERROR] 404 Not Found: {ENDPOINT}")
            print("[SUGGESTION] Check CATAPULT_BASE_URL region and API version in your Catapult docs.")
        else:
            print(f"[FAILED] Received HTTP code {response.status_code}")
            print(f"Details: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"[CONNECTION ERROR] Could not reach the Catapult server. Details: {str(e)}")

if __name__ == "__main__":
    run_handshake()