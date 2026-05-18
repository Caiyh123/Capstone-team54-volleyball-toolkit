"""Flatten GymAware API JSON into scalar dicts for BI tables."""
from __future__ import annotations

import re
from typing import Any

_BAR_WEIGHT_RE = re.compile(r"^([\d.+-]+)")


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_bar_weight(v: Any) -> float | None:
    """API may return barWeight as a number or a string like ``50.0 kg``."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    m = _BAR_WEIGHT_RE.match(s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return _num(v)


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _target_band(obj: Any, key: str) -> tuple[float | None, float | None]:
    if not isinstance(obj, dict):
        return None, None
    band = obj.get(key)
    if not isinstance(band, dict):
        return None, None
    return _num(band.get("max")), _num(band.get("min"))


def summary_bi_fields(row: dict[str, Any]) -> dict[str, Any]:
    targets = row.get("targets") if isinstance(row.get("targets"), dict) else {}
    best_max, best_min = _target_band(targets, "best")
    last_max, last_min = _target_band(targets, "last")
    squad_max, squad_min = _target_band(targets, "squad")
    preset_max, preset_min = _target_band(targets, "preset")
    return {
        "gymaware_reference": str(row["reference"]) if row.get("reference") is not None else None,
        "recorded": _num(row.get("recorded")),
        "modified": _num(row.get("modified")),
        "athlete_reference": str(row["athleteReference"])
        if row.get("athleteReference") is not None
        else None,
        "athlete_name": row.get("athleteName"),
        "athlete_weight": _num(row.get("athleteWeight")),
        "exercise_name": row.get("exerciseName"),
        "exercise_reference": str(row["exerciseReference"])
        if row.get("exerciseReference") is not None
        else None,
        "bar_weight": parse_bar_weight(row.get("barWeight")),
        "rep_count": _int(row.get("repCount")),
        "height": _num(row.get("height")),
        "dip": _num(row.get("dip")),
        "mean_velocity": _num(row.get("meanVelocity")),
        "peak_velocity": _num(row.get("peakVelocity")),
        "mean_power": _num(row.get("meanPower")),
        "peak_power": _num(row.get("peakPower")),
        "mean_watts_per_kg": _num(row.get("meanWattsPerKg")),
        "peak_watts_per_kg": _num(row.get("peakWattsPerKg")),
        "velocity_zone": row.get("velocityZone"),
        "activity_name": row.get("activityName"),
        "activity_reference": row.get("activityReference"),
        "sensor": row.get("sensor"),
        "hardware": row.get("hardware"),
        "notes": row.get("notes"),
        "deleted": _bool(row.get("deleted")),
        "targets_mode": targets.get("mode"),
        "targets_analysis": targets.get("analysis"),
        "targets_best_max": best_max,
        "targets_best_min": best_min,
        "targets_last_max": last_max,
        "targets_last_min": last_min,
        "targets_squad_max": squad_max,
        "targets_squad_min": squad_min,
        "targets_preset_max": preset_max,
        "targets_preset_min": preset_min,
    }


def best_bi_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "athlete_reference": str(row["athleteReference"])
        if row.get("athleteReference") is not None
        else None,
        "athlete_name": row.get("athleteName"),
        "exercise_name": row.get("exerciseName"),
        "bar_weight": parse_bar_weight(row.get("barWeight")),
        "height": _num(row.get("height")),
        "dip": _num(row.get("dip")),
        "mean_velocity": _num(row.get("meanVelocity")),
        "peak_velocity": _num(row.get("peakVelocity")),
        "mean_power": _num(row.get("meanPower")),
        "peak_power": _num(row.get("peakPower")),
        "mean_watts_per_kg": _num(row.get("meanWattsPerKg")),
        "peak_watts_per_kg": _num(row.get("peakWattsPerKg")),
    }


def athlete_bi_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "athlete_reference": str(row["athleteReference"])
        if row.get("athleteReference") is not None
        else None,
        "display_name": row.get("displayName"),
        "first_name": row.get("firstName"),
        "last_name": row.get("lastName"),
        "jersey_number": row.get("jerseyNumber"),
        "position": row.get("position"),
        "sport": row.get("sport"),
        "address": row.get("address"),
        "phone": row.get("phone"),
        "born": row.get("born"),
        "photo": row.get("photo"),
        "modified": _num(row.get("modified")),
    }


def rep_bi_fields(set_row: dict[str, Any], rep: dict[str, Any], rep_index: int) -> dict[str, Any]:
    """One row per rep; per-rep analysis metrics stored in rep_metrics (JSONB)."""
    return {
        "set_reference": str(set_row["reference"]) if set_row.get("reference") is not None else None,
        "recorded": _num(set_row.get("recorded")),
        "modified": _num(set_row.get("modified")),
        "athlete_reference": str(set_row["athleteReference"])
        if set_row.get("athleteReference") is not None
        else None,
        "athlete_name": set_row.get("athleteName"),
        "athlete_weight": _num(set_row.get("athleteWeight")),
        "exercise_name": set_row.get("exerciseName"),
        "exercise_reference": str(set_row["exerciseReference"])
        if set_row.get("exerciseReference") is not None
        else None,
        "bar_weight": parse_bar_weight(set_row.get("barWeight")),
        "rep_count": _int(set_row.get("repCount")),
        "activity_name": set_row.get("activityName"),
        "activity_reference": set_row.get("activityReference"),
        "rep_num": _int(rep.get("REPNUM")) if isinstance(rep, dict) else rep_index,
        "rep_metrics": rep if isinstance(rep, dict) else {},
    }
