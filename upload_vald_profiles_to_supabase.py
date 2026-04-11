"""
Fetch VALD External Profiles (GET /profiles per tenant) and upsert into public.vald_profiles.

Prerequisites:
  1. schema/vald_profiles.sql applied in Supabase.
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

from integrations.vald.client import ValdClient
from integrations.vald.profiles import flatten_vald_profiles_response

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "").strip()

UPSERT_SQL = """
INSERT INTO public.vald_profiles (
    tenant_id, profile_id, sync_id, given_name, family_name, date_of_birth,
    external_id, email, group_id, being_merged_with_profile_id,
    being_merged_with_expiry_utc, raw, updated_at
) VALUES (
    %(tenant_id)s, %(profile_id)s, %(sync_id)s, %(given_name)s, %(family_name)s, %(date_of_birth)s,
    %(external_id)s, %(email)s, %(group_id)s, %(being_merged_with_profile_id)s,
    %(being_merged_with_expiry_utc)s, %(raw)s, NOW()
)
ON CONFLICT (tenant_id, profile_id) DO UPDATE SET
    sync_id = EXCLUDED.sync_id,
    given_name = EXCLUDED.given_name,
    family_name = EXCLUDED.family_name,
    date_of_birth = EXCLUDED.date_of_birth,
    external_id = EXCLUDED.external_id,
    email = EXCLUDED.email,
    group_id = EXCLUDED.group_id,
    being_merged_with_profile_id = EXCLUDED.being_merged_with_profile_id,
    being_merged_with_expiry_utc = EXCLUDED.being_merged_with_expiry_utc,
    raw = EXCLUDED.raw,
    updated_at = NOW()
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
    parser = argparse.ArgumentParser(description="Upsert VALD profiles into Supabase")
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
                try:
                    cur.execute(UPSERT_SQL, mapped)
                    ok += 1
                except Exception as e:
                    print(f"  [WARNING] profile skip: {e}")
                    skipped += 1
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database error: {e}", file=sys.stderr)
        return 1

    print(f"\n[SUCCESS] Upserted {ok} row(s); skipped {skipped}.")
    print("[CHECK] SELECT COUNT(*) FROM public.vald_profiles;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
