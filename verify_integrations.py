"""
Quick check that Catapult + GymAware (+ optional VALD) credentials work.

Run: python verify_integrations.py
"""
from __future__ import annotations

import sys

import requests
from dotenv import load_dotenv

load_dotenv()

from integrations import config
from integrations.gymaware.client import GymAwareClient
from integrations.vald.client import ValdClient


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


def check_vald() -> bool | None:
    """Returns None if VALD not configured."""
    if not config.vald_settings()["client_id"]:
        print("[VALD] SKIP: VALD_CLIENT_ID not set.")
        return None
    try:
        client = ValdClient()
        tenants = client.list_tenants()
    except Exception as e:
        print(f"[VALD] FAIL: {e}")
        return False
    n = len(tenants) if isinstance(tenants, list) else 1
    print(f"[VALD] OK - tenants response received ({n} item(s) if list).")
    return True


def main() -> int:
    print("Verifying integrations (Catapult + GymAware; VALD if configured)...\n")
    c = check_catapult()
    g = check_gymaware()
    v = check_vald()
    print()
    if not c or not g:
        print("Catapult/GymAware need attention; check .env against .env.example.")
        return 1
    if v is False:
        return 1
    if v is None:
        print("Catapult + GymAware OK. (VALD not configured — optional.)")
    else:
        print("Catapult + GymAware + VALD OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
