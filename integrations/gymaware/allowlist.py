"""
Load GymAware athlete allowlist from the client's reference workbook.

Default path: GymAware API Reference Numbers.xlsx in project root, or GYMAWARE_ALLOWLIST_XLSX.
Use for Option A privacy filtering (summaries/reps → only rows whose athleteReference is in the set).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_REL = "GymAware API Reference Numbers.xlsx"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_allowlist_path(path: str | Path | None) -> Path:
    if path:
        return Path(path)
    p = os.getenv("ROSTER_ALLOWLIST_XLSX", "").strip()
    if p:
        return Path(p)
    p = os.getenv("GYMAWARE_ALLOWLIST_XLSX", "").strip()
    if p:
        return Path(p)
    return _project_root() / DEFAULT_REL


def load_athlete_references_from_xlsx(
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], set[int]]:
    """
    Parse roster workbook (sheet GymAware when present): Last Name, First Name, GymAware API ID.
    Legacy workbooks with index column still supported via integrations.roster_allowlist.

    Returns (rows_as_dicts, reference_id_set).
    """
    from integrations.roster_allowlist import load_roster_allowlist

    path = _resolve_allowlist_path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Allowlist workbook not found: {path}")

    rows_out, allow = load_roster_allowlist(path)
    refs = set(allow.gymaware_refs)
    compat = [
        {
            "last_name": r.get("last_name", ""),
            "first_name": r.get("first_name", ""),
            "athlete_reference": r["athlete_reference"],
        }
        for r in rows_out
    ]
    return compat, refs


def athlete_reference_allowlist() -> set[int]:
    """Convenience: only the GymAware athleteReference IDs."""
    _, refs = load_athlete_references_from_xlsx()
    return refs


def env_use_allowlist() -> bool:
    """True when ROSTER_FILTER or GYMAWARE_USE_ALLOWLIST enables workbook-based filtering."""
    from integrations.roster_allowlist import env_roster_filter_enabled

    if env_roster_filter_enabled():
        return True
    v = os.getenv("GYMAWARE_USE_ALLOWLIST", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def filter_rows_by_athlete_reference(
    rows: list[dict[str, Any]],
    allow: set[int],
) -> list[dict[str, Any]]:
    """Keep API rows whose athleteReference is in allow (GymAware camelCase)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        ar = row.get("athleteReference")
        try:
            ar_int = int(ar) if ar is not None else None
        except (TypeError, ValueError):
            continue
        if ar_int is not None and ar_int in allow:
            out.append(row)
    return out
