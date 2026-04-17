"""
Fetch VALD External Profiles (GET /profiles per tenant) and append rows to public.vald_profiles.

Prerequisites:
  1. schema/vald_profiles.sql and schema/medallion_raw_layer_migration.sql applied in Supabase.
  2. VALD_CLIENT_ID, VALD_CLIENT_SECRET, DATABASE_URL in .env

Run:
  python upload_vald_profiles_to_supabase.py
  python upload_vald_profiles_to_supabase.py --tenant-id <uuid>
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

from integrations.roster_allowlist import env_roster_filter_enabled, load_roster_allowlist
from integrations.vald.client import ValdClient
from integrations.vald.profiles import flatten_vald_profiles_response

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "").strip()

INSERT_SQL = """
INSERT INTO public.vald_profiles (
    tenant_id, profile_id, sync_id, given_name, family_name, date_of_birth,
    external_id, email, group_id, being_merged_with_profile_id,
    being_merged_with_expiry_utc, raw, updated_at, etl_ingested_at
) VALUES (
    %(tenant_id)s, %(profile_id)s, %(sync_id)s, %(given_name)s, %(family_name)s, %(date_of_birth)s,
    %(external_id)s, %(email)s, %(group_id)s, %(being_merged_with_profile_id)s,
    %(being_merged_with_expiry_utc)s, %(raw)s, NOW(), NOW()
)
"""


def _parse_ts(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (datetime,)):
        return v
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _group_id_str(p: dict[str, Any]) -> str | None:
    g = p.get("groupId")
    if g is None:
        return None
    if isinstance(g, list):
        if not g:
            return None
        return ",".join(str(x) for x in g)
    return str(g)


def map_profile(tenant_id: str, p: dict[str, Any]) -> dict[str, Any] | None:
    pid = p.get("profileId")
    if pid is None:
        pid = p.get("profile_id")
    if pid is None:
        return None
    return {
        "tenant_id": tenant_id.strip(),
        "profile_id": str(pid),
        "sync_id": (p.get("syncId") or p.get("sync_id")),
        "given_name": p.get("givenName") or p.get("given_name"),
        "family_name": p.get("familyName") or p.get("family_name"),
        "date_of_birth": _parse_ts(p.get("dateOfBirth") or p.get("date_of_birth")),
        "external_id": p.get("externalId") or p.get("external_id"),
        "email": p.get("email"),
        "group_id": _group_id_str(p),
        "being_merged_with_profile_id": (
            str(x)
            if (x := p.get("beingMergedWithProfileId") or p.get("being_merged_with_profile_id"))
            is not None
            else None
        ),
        "being_merged_with_expiry_utc": _parse_ts(
            p.get("beingMergedWithProfileExpiryDateUtc")
            or p.get("being_merged_with_profile_expiry_date_utc")
        ),
        "raw": Json(p),
    }


def tenant_ids_from_api(client: ValdClient, single: str | None) -> list[str]:
    if single and single.strip():
        return [single.strip()]
    raw = client.list_tenants()
    ids: list[str] = []
    if isinstance(raw, list):
        for t in raw:
            if isinstance(t, dict) and t.get("id") is not None:
                ids.append(str(t["id"]))
    elif isinstance(raw, dict):
        inner = raw.get("tenants") or raw.get("items") or raw.get("data")
        if isinstance(inner, list):
            for t in inner:
                if isinstance(t, dict) and t.get("id") is not None:
                    ids.append(str(t["id"]))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Append VALD profile rows into Supabase (raw layer)")
    parser.add_argument("--tenant-id", default="", help="Only sync this tenant UUID")
    args = parser.parse_args()

    if not DB_URL:
        print("[ERROR] DATABASE_URL not set in .env", file=sys.stderr)
        return 1

    try:
        client = ValdClient()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    tids = tenant_ids_from_api(client, args.tenant_id or None)
    if not tids:
        print("[ERROR] No tenant ids returned. Check VALD credentials and region API bases.")
        return 1

    print(f"[INFO] Tenants to sync: {len(tids)}")

    allowed_vald: set[str] | None = None
    if env_roster_filter_enabled():
        try:
            _, roster = load_roster_allowlist()
        except FileNotFoundError as e:
            print(f"[ERROR] ROSTER_FILTER=1 but roster workbook missing: {e}", file=sys.stderr)
            return 1
        allowed_vald = {v.lower() for v in roster.vald_profile_ids}
        if not allowed_vald:
            print(
                "[ERROR] ROSTER_FILTER=1 but roster workbook has no Vald Profile_ID values.",
                file=sys.stderr,
            )
            return 1
        print(
            f"[INFO] ROSTER_FILTER: VALD insert limited to {len(allowed_vald)} profile id(s).",
            file=sys.stderr,
        )

    ok = 0
    skipped = 0
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        for tid in tids:
            try:
                raw_profiles = client.list_profiles(tid)
            except Exception as e:
                print(f"  [WARNING] tenant {tid}: fetch failed: {e}")
                continue
            rows = flatten_vald_profiles_response(raw_profiles)
            print(f"  [INFO] tenant {tid}: {len(rows)} profile(s) (after flattening groups)")
            for p in rows:
                mapped = map_profile(tid, p)
                if not mapped:
                    skipped += 1
                    continue
                if allowed_vald is not None:
                    pid = str(mapped["profile_id"]).strip().lower()
                    if pid not in allowed_vald:
                        skipped += 1
                        continue
                try:
                    cur.execute(INSERT_SQL, mapped)
                    ok += 1
                except Exception as e:
                    print(f"  [WARNING] profile skip: {e}")
                    skipped += 1
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database error: {e}", file=sys.stderr)
        return 1

    print(f"\n[SUCCESS] Inserted {ok} row(s); skipped {skipped}.")
    print("[CHECK] SELECT COUNT(*) FROM public.vald_profiles;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
