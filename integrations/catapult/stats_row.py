"""Normalize athlete id from a Catapult /stats JSON row."""
from __future__ import annotations

from typing import Any


def athlete_jersey_from_stats_row(row: dict[str, Any]) -> str | None:
    """Jersey label from POST /stats row (OpenField often uses this when athlete UUID is absent)."""
    j = row.get("athlete_jersey")
    if j is None:
        return None
    s = str(j).strip()
    return s if s else None


def jersey_from_activity_athlete(ath: dict[str, Any]) -> str | None:
    """Jersey from GET /activities/{id}/athletes item."""
    for key in ("athlete_jersey", "jersey", "jersey_number", "player_jersey", "athleteJersey"):
        v = ath.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


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
