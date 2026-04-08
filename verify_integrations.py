"""
Quick check that Catapult + GymAware credentials work (current integration scope).

Run: python verify_integrations.py
"""
from __future__ import annotations

import sys

import requests
from dotenv import load_dotenv

load_dotenv()

from integrations import config
from integrations.gymaware.client import GymAwareClient


def check_catapult() -> bool:
    try:
        token = config.catapult_token()
        base = config.catapult_base_url()
    except RuntimeError as e:
        print(f"[Catapult] SKIP: {e}")
        return False

    r = requests.get(
        f"{base}/athletes",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"[Catapult] FAIL HTTP {r.status_code}: {r.text[:200]}")
        return False

    data = r.json()
    rows = data if isinstance(data, list) else data.get("data", [])
    print(f"[Catapult] OK - {len(rows)} athlete row(s) visible.")
    return True


def check_gymaware() -> bool:
    try:
        client = GymAwareClient()
    except RuntimeError as e:
        print(f"[GymAware] SKIP: {e}")
        return False

    try:
        athletes = client.list_athletes()
    except Exception as e:
        print(f"[GymAware] FAIL: {e}")
        return False

    print(f"[GymAware] OK - {len(athletes)} athlete row(s) from API.")
    return True


def main() -> int:
    print("Verifying active integrations (Catapult + GymAware)...\n")
    c = check_catapult()
    g = check_gymaware()
    print()
    if c and g:
        print("All configured sources responded successfully.")
        return 0
    if not c and not g:
        print("Neither source is fully configured; check .env against .env.example.")
        return 1
    print("Partial success — fix the failed source above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
