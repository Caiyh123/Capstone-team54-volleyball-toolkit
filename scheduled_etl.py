"""
Run scheduled ETL for multiple sources using the repo's existing scripts.

Each source is optional; use --sources or --all. Runs subprocesses from the repo root
so .env and relative paths (e.g. GymAware allowlist, Catapult JSON) resolve as usual.

Examples:
  python scheduled_etl.py --all
  python scheduled_etl.py --sources catapult,gymaware
  python scheduled_etl.py --all --gymaware-lookback-days 7 --whoop-lookback-days 14
  python scheduled_etl.py --all --continue-on-error

Env (optional defaults for lookback windows):
  SCHEDULED_GYMAWARE_LOOKBACK_DAYS, SCHEDULED_WHOOP_LOOKBACK_DAYS,
  SCHEDULED_LOAD_INDEX_LOOKBACK_DAYS, SCHEDULED_SKIP_ROSTER_SYNC

Load index: after load_index.py, runs upload_load_index_to_supabase.py (needs DATABASE_URL).
VALD: vald_export + profile upload + optional ForceFrame tests + optional ForceDecks (VA package grain).
  VALD_SKIP_FORCEFRAME_TESTS=1 skips ForceFrame only; VALD_SKIP_FORCEDECKS=1 skips ForceDecks only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
PY = sys.executable

KNOWN_SOURCES = ("catapult", "gymaware", "vald", "whoop", "load_index")


def run_roster_sync() -> int:
    """Push committed roster workbook into roster_cohort + athlete_identity."""
    rc = _run_step(
        "Roster cohort sync (from workbook)",
        [ROOT / "scripts" / "sync_roster_cohort_from_xlsx.py"],
    )
    if rc != 0:
        return rc
    return _run_step(
        "Athlete identity sync (from workbook)",
        [ROOT / "scripts" / "sync_athlete_identity_from_xlsx.py"],
    )


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _utc_inclusive_range(lookback_days: int) -> tuple[str, str]:
    """Last N calendar days inclusive ending today (UTC)."""
    n = max(1, lookback_days)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()


def _run_step(label: str, args: Sequence[Path | str]) -> int:
    cmd = [PY, *[str(a) for a in args]]
    print(f"\n{'=' * 60}\n[{label}]\n$ {' '.join(cmd)}\n{'=' * 60}\n", flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def run_catapult() -> int:
    rc = _run_step("Catapult bulk_export", [ROOT / "bulk_export.py"])
    if rc != 0:
        return rc
    return _run_step("Catapult upload_to_supabase", [ROOT / "upload_to_supabase.py"])


def run_gymaware(start: str, end: str) -> int:
    rc = _run_step(
        "GymAware export",
        [
            ROOT / "gymaware_export.py",
            "--start",
            start,
            "--end",
            end,
        ],
    )
    if rc != 0:
        return rc
    return _run_step("GymAware upload", [ROOT / "upload_gymaware_to_supabase.py"])


VALD_SNAPSHOT_JSON = ROOT / "vald_snapshot.json"


def run_vald(tenant_id: str | None) -> int:
    cmd: list[Path | str] = [
        ROOT / "vald_export.py",
        "--profiles",
        "--out",
        str(VALD_SNAPSHOT_JSON),
    ]
    if tenant_id:
        cmd.extend(["--tenant-id", tenant_id])
    rc = _run_step("VALD export (tenants + profiles JSON)", cmd)
    if rc != 0:
        return rc
    up: list[Path | str] = [ROOT / "upload_vald_profiles_to_supabase.py"]
    if tenant_id:
        up.extend(["--tenant-id", tenant_id])
    rc = _run_step("VALD profiles upload", up)
    if rc != 0:
        return rc
    skip_ff = os.getenv("VALD_SKIP_FORCEFRAME_TESTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if not skip_ff:
        ff_cmd: list[Path | str] = [ROOT / "upload_vald_forceframe_tests_to_supabase.py"]
        if tenant_id:
            ff_cmd.extend(["--tenant-id", tenant_id])
        rc = _run_step("VALD ForceFrame tests (activity) upload", ff_cmd)
        if rc != 0:
            return rc

    skip_fd = os.getenv("VALD_SKIP_FORCEDECKS", "").strip().lower() in ("1", "true", "yes")
    if skip_fd:
        return 0
    fd_cmd: list[Path | str] = [ROOT / "upload_vald_forcedecks_to_supabase.py"]
    if tenant_id:
        fd_cmd.extend(["--tenant-id", tenant_id])
    return _run_step("VALD ForceDecks (tests/trials) upload", fd_cmd)


def run_whoop(lookback: int, resources: str, dry_run: bool) -> int:
    cmd: list[Path | str] = [
        ROOT / "whoop_etl.py",
        "--lookback-days",
        str(lookback),
        "--resources",
        resources,
    ]
    if dry_run:
        cmd.append("--dry-run")
    return _run_step("WHOOP ETL", cmd)


def run_load_index(start: str, end: str) -> int:
    rc = _run_step(
        "Catapult load_index",
        [
            ROOT / "load_index.py",
            "--start",
            start,
            "--end",
            end,
        ],
    )
    if rc != 0:
        return rc
    return _run_step(
        "Load index upload to Supabase",
        [ROOT / "upload_load_index_to_supabase.py"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrate scheduled ETL (Catapult, GymAware, VALD profiles, WHOOP, load index+upload)."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Run all sources: {', '.join(KNOWN_SOURCES)}",
    )
    parser.add_argument(
        "--sources",
        default="",
        help=f"Comma-separated subset of: {','.join(KNOWN_SOURCES)}",
    )
    parser.add_argument(
        "--gymaware-lookback-days",
        type=int,
        default=_env_int("SCHEDULED_GYMAWARE_LOOKBACK_DAYS", 7),
        help="UTC date window for GymAware export (default 7 or SCHEDULED_GYMAWARE_LOOKBACK_DAYS)",
    )
    parser.add_argument(
        "--whoop-lookback-days",
        type=int,
        default=_env_int(
            "SCHEDULED_WHOOP_LOOKBACK_DAYS",
            _env_int("WHOOP_ETL_LOOKBACK_DAYS", 14),
        ),
        help="WHOOP API window (default from env or 14)",
    )
    parser.add_argument(
        "--whoop-resources",
        default=os.getenv("WHOOP_ETL_RESOURCES", "sleep,workout,cycle,recovery"),
        help="Passed to whoop_etl.py --resources",
    )
    parser.add_argument(
        "--load-index-lookback-days",
        type=int,
        default=_env_int("SCHEDULED_LOAD_INDEX_LOOKBACK_DAYS", 7),
        help="UTC date window for load_index.py (default 7)",
    )
    parser.add_argument(
        "--vald-tenant-id",
        default="",
        help="If set, only this tenant for VALD profile upload (else all tenants)",
    )
    parser.add_argument(
        "--whoop-dry-run",
        action="store_true",
        help="Pass --dry-run to whoop_etl (no staging writes)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Run remaining sources after a failure (default: stop on first non-zero exit). "
        "Exit code is still non-zero if any source failed.",
    )
    args = parser.parse_args()

    if args.all:
        want = list(KNOWN_SOURCES)
    else:
        raw = [x.strip().lower() for x in args.sources.split(",") if x.strip()]
        if not raw:
            parser.error("Specify --all or --sources catapult,gymaware,...")
        unknown = [x for x in raw if x not in KNOWN_SOURCES]
        if unknown:
            parser.error(f"Unknown sources: {unknown}. Valid: {list(KNOWN_SOURCES)}")
        want = raw

    ga_start, ga_end = _utc_inclusive_range(args.gymaware_lookback_days)
    li_start, li_end = _utc_inclusive_range(args.load_index_lookback_days)

    summary: dict[str, object] = {
        "sources": want,
        "windows": {
            "gymaware_utc": [ga_start, ga_end],
            "load_index_utc": [li_start, li_end],
            "whoop_lookback_days": args.whoop_lookback_days,
        },
        "steps": [],
    }
    failed: list[str] = []

    skip_roster = os.getenv("SCHEDULED_SKIP_ROSTER_SYNC", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if not skip_roster:
        rc_roster = run_roster_sync()
        summary["steps"].append({"name": "roster_sync", "exit_code": rc_roster})
        if rc_roster != 0:
            failed.append("roster_sync")
            if not args.continue_on_error:
                print("\n" + json.dumps({**summary, "failed": failed, "ok": False}, indent=2), flush=True)
                return 1

    def record(name: str, rc: int) -> bool:
        summary["steps"].append({"name": name, "exit_code": rc})
        if rc != 0:
            failed.append(name)
            return False
        return True

    for src in want:
        rc = 0
        if src == "catapult":
            rc = run_catapult()
            record("catapult", rc)
        elif src == "gymaware":
            rc = run_gymaware(ga_start, ga_end)
            record("gymaware", rc)
        elif src == "vald":
            tid = args.vald_tenant_id.strip() or None
            rc = run_vald(tid)
            record("vald", rc)
        elif src == "whoop":
            rc = run_whoop(args.whoop_lookback_days, args.whoop_resources, args.whoop_dry_run)
            record("whoop", rc)
        elif src == "load_index":
            rc = run_load_index(li_start, li_end)
            record("load_index", rc)

        if rc != 0 and not args.continue_on_error:
            break

    summary["failed"] = failed
    summary["ok"] = len(failed) == 0

    print("\n" + json.dumps(summary, indent=2), flush=True)

    # --continue-on-error only controls whether we stop after the first failure; the process
    # should still exit non-zero if any step failed so CI / schedulers reflect real pipeline health.
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
