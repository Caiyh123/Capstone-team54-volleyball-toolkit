"""
Upsert public.athlete_identity from the client roster workbook (ROSTER_ALLOWLIST_XLSX).

Uses GymAware API ID as the stable join key. internal_key defaults to VB-{gymaware_ref}
unless the sheet has a Global Athlete ID / internal key column.

Requires: DATABASE_URL, schema/athlete_identity.sql applied.
Run after coaches update roster_new.xlsx (including WHOOP user IDs when available):

  python scripts/sync_athlete_identity_from_xlsx.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from integrations.roster_allowlist import load_roster_allowlist  # noqa: E402

UPSERT = """
INSERT INTO public.athlete_identity (
    internal_key,
    display_name,
    catapult_athlete_id,
    gymaware_athlete_reference,
    vald_profile_id,
    whoop_user_id,
    updated_at
) VALUES (
    %(internal_key)s,
    %(display_name)s,
    %(catapult_athlete_id)s,
    %(gymaware_athlete_reference)s,
    %(vald_profile_id)s,
    %(whoop_user_id)s,
    NOW()
)
ON CONFLICT (internal_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    catapult_athlete_id = COALESCE(EXCLUDED.catapult_athlete_id, athlete_identity.catapult_athlete_id),
    gymaware_athlete_reference = EXCLUDED.gymaware_athlete_reference,
    vald_profile_id = COALESCE(EXCLUDED.vald_profile_id, athlete_identity.vald_profile_id),
    whoop_user_id = COALESCE(EXCLUDED.whoop_user_id, athlete_identity.whoop_user_id),
    updated_at = NOW()
"""


def main() -> int:
    db = os.getenv("DATABASE_URL", "").strip()
    if not db:
        print("[ERROR] DATABASE_URL not set.", file=sys.stderr)
        return 1

    try:
        rows, _allow = load_roster_allowlist()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        n = 0
        for r in rows:
            ref = r["athlete_reference"]
            internal_key = (r.get("internal_key") or "").strip() or f"VB-{ref}"
            ln = r.get("last_name") or ""
            fn = r.get("first_name") or ""
            display = f"{ln}, {fn}".strip(", ") or None
            cur.execute(
                UPSERT,
                {
                    "internal_key": internal_key,
                    "display_name": display,
                    "catapult_athlete_id": r.get("catapult_athlete_id"),
                    "gymaware_athlete_reference": ref,
                    "vald_profile_id": r.get("vald_profile_id"),
                    "whoop_user_id": r.get("whoop_user_id"),
                },
            )
            n += 1
        cur.close()
    finally:
        conn.close()

    print(f"[SUCCESS] athlete_identity upserted {n} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
