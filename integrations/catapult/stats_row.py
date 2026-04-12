"""Normalize athlete id from a Catapult /stats JSON row."""
from __future__ import annotations

from typing import Any


def athlete_id_from_stats_row(row: dict[str, Any]) -> str | None:
    """Best-effort UUID string for participating athlete."""
    aid = row.get("athlete_id")
    if aid:
        return str(aid)
    pa = row.get("participating_athlete")
    if isinstance(pa, dict):
        pid = pa.get("id")
        if pid:
            return str(pid)
    pid = row.get("participating_athlete_id")
    if pid:
        return str(pid)
    return None


def activity_id_from_stats_row(row: dict[str, Any]) -> str | None:
    v = row.get("source_activity_id")
    return str(v) if v else None
