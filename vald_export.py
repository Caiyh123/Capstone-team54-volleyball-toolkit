"""
Smoke test / export: VALD External Tenants + Profiles (read-only).

Requires .env:
  VALD_CLIENT_ID, VALD_CLIENT_SECRET
Optional:
  VALD_OAUTH_TOKEN_URL, VALD_OAUTH_AUDIENCE
  VALD_API_BASE_TENANTS, VALD_API_BASE_PROFILE (AUE defaults)

Examples:
  python vald_export.py
  python vald_export.py --profiles
  python vald_export.py --tenant-id <uuid> --profiles
  python vald_export.py --out vald_tenants.json
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from integrations.vald.client import ValdClient
from integrations.vald.profiles import flatten_vald_profiles_response


def _write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="VALD tenants/profiles export (read API)")
    parser.add_argument(
        "--profiles",
        action="store_true",
        help="Also fetch GET /profiles for each tenant (or --tenant-id only)",
    )
    parser.add_argument(
        "--tenant-id",
        dest="tenant_id",
        default="",
        help="Limit profile fetch to this tenant UUID",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Write combined JSON to this file (default: print tenants only to stdout)",
    )
    args = parser.parse_args()

    try:
        client = ValdClient()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    tenants = client.list_tenants()
    out: dict[str, Any] = {"tenants": tenants}

    if args.profiles:
        tenant_ids: list[str] = []
        if args.tenant_id.strip():
            tenant_ids = [args.tenant_id.strip()]
        else:
            # Normalize tenant list to ids
            if isinstance(tenants, list):
                for t in tenants:
                    if isinstance(t, dict) and t.get("id") is not None:
                        tenant_ids.append(str(t["id"]))
            elif isinstance(tenants, dict):
                # Some APIs wrap collections
                inner = tenants.get("tenants") or tenants.get("items") or tenants.get("data")
                if isinstance(inner, list):
                    for t in inner:
                        if isinstance(t, dict) and t.get("id") is not None:
                            tenant_ids.append(str(t["id"]))

        profiles_by_tenant: dict[str, Any] = {}
        summary: dict[str, int] = {}
        for tid in tenant_ids:
            try:
                raw = client.list_profiles(tid)
                profiles_by_tenant[tid] = raw
                n = len(flatten_vald_profiles_response(raw))
                summary[tid] = n
            except Exception as ex:
                profiles_by_tenant[tid] = {"error": str(ex)}
        out["profiles_by_tenant"] = profiles_by_tenant
        out["profile_counts_flattened"] = summary

    if args.out:
        _write_json(args.out, out)
        print(f"[OK] Wrote {args.out}")
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    if args.profiles and out.get("profile_counts_flattened"):
        print(
            "\n[INFO] Profiles per tenant (flattened from groups, deduped):",
            file=sys.stderr,
        )
        for tid, n in out["profile_counts_flattened"].items():
            print(f"  {tid}: {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
