"""
Offline check: which integration env vars are set (yes/no only — never prints secrets).

Run from repo root: python scripts/preflight_config.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _has(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _line(label: str, ok: bool) -> None:
    status = "yes" if ok else "no"
    print(f"  {label}: {status}")


def main() -> int:
    print(f"Preflight (repo root: {ROOT})\n")
    print("Core:")
    _line("DATABASE_URL", _has("DATABASE_URL"))

    print("\nCatapult:")
    _line("CATAPULT_TOKEN", _has("CATAPULT_TOKEN"))

    print("\nGymAware:")
    _line("GYMAWARE_ACCOUNT_ID", _has("GYMAWARE_ACCOUNT_ID"))
    _line("GYMAWARE_TOKEN", _has("GYMAWARE_TOKEN"))

    print("\nVALD (optional for scheduled_etl vald step):")
    _line("VALD_CLIENT_ID", _has("VALD_CLIENT_ID"))
    _line("VALD_CLIENT_SECRET", _has("VALD_CLIENT_SECRET"))

    print("\nWHOOP Auth Bridge + ETL:")
    _line("WHOOP_CLIENT_ID", _has("WHOOP_CLIENT_ID"))
    _line("WHOOP_CLIENT_SECRET", _has("WHOOP_CLIENT_SECRET"))
    _line("WHOOP_REDIRECT_URI", _has("WHOOP_REDIRECT_URI"))

    print("\nCopy .env.example to .env and fill values; apply schema/apply_order.txt in Supabase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
