"""
Upsert public.roster_cohort from the client roster workbook (same source as ROSTER_ALLOWLIST_XLSX).

Requires: DATABASE_URL, schema/roster_cohort.sql applied.

Run from toolkit root:
  python scripts/sync_roster_cohort_from_xlsx.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Toolkit .env first, then repo parent (e.g. Volley/.env) so DATABASE_URL is found.
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parent / ".env")

# Allow running as script: add toolkit root to path
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from integrations.roster_allowlist import load_roster_allowlist  # noqa: E402

UPSERT = """
INSERT INTO public.roster_cohort (gymaware_athlete_reference, vald_profile_id, display_label, catapult_jersey, updated_at)
VALUES (%(gymaware_athlete_reference)s, %(vald_profile_id)s, %(display_label)s, %(catapult_jersey)s, NOW())
ON CONFLICT (gymaware_athlete_reference) DO UPDATE SET
    vald_profile_id = EXCLUDED.vald_profile_id,
    display_label = EXCLUDED.display_label,
    catapult_jersey = EXCLUDED.catapult_jersey,
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
            ln = r.get("last_name") or ""
            fn = r.get("first_name") or ""
            label = f"{ln}, {fn}".strip(", ")
            vp = r.get("vald_profile_id")
            cj = r.get("catapult_jersey")
            cur.execute(
                UPSERT,
                {
                    "gymaware_athlete_reference": ref,
                    "vald_profile_id": vp,
                    "display_label": label or None,
                    "catapult_jersey": cj,
                },
            )
            n += 1
        cur.close()
    finally:
        conn.close()

    print(f"[SUCCESS] roster_cohort upserted {n} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
