"""
Normalize VALD GET /profiles JSON — responses may be a flat list or grouped by `groups[].profiles[]`
(March 2026+). See External Profiles API docs.
"""
from __future__ import annotations

from typing import Any


def flatten_vald_profiles_response(data: Any) -> list[dict[str, Any]]:
    """
    Return every profile object from a /profiles response, injecting groupId from the parent group when missing.

    Handles:
    - JSON array of profile objects
    - `{ "profiles": [...] }` (and items/data/results/value)
    - `{ "groups": [{ "groupId", "profiles": [...] }, ...] }` (possibly nested under tenant keys)
    """
    acc: list[dict[str, Any]] = []

    def is_profile(d: dict[str, Any]) -> bool:
        return "profileId" in d or "profile_id" in d

    def append_profiles(lst: list[Any], default_group: str | None) -> None:
        for item in lst:
            if not isinstance(item, dict) or not is_profile(item):
                continue
            d = dict(item)
            if default_group is not None and d.get("groupId") is None and d.get("group_id") is None:
                d["groupId"] = default_group
            acc.append(d)

    if data is None:
        return []

    if isinstance(data, list):
        append_profiles(data, None)
        return _dedupe_by_profile_id(acc)

    if isinstance(data, dict):
        for key in ("profiles", "items", "data", "results", "value"):
            inner = data.get(key)
            if isinstance(inner, list) and inner and isinstance(inner[0], dict) and is_profile(inner[0]):
                append_profiles(inner, None)
                return _dedupe_by_profile_id(acc)

        groups = data.get("groups")
        if isinstance(groups, list):
            for g in groups:
                if not isinstance(g, dict):
                    continue
                gid = g.get("groupId") or g.get("group_id")
                plist = g.get("profiles")
                if isinstance(plist, list):
                    gs = str(gid) if gid is not None else None
                    append_profiles(plist, gs)

        if not acc:
            acc.extend(_profiles_from_nested_groups(data, depth=0))

    return _dedupe_by_profile_id(acc)


def _profiles_from_nested_groups(obj: Any, depth: int) -> list[dict[str, Any]]:
    """Find groups[].profiles[] anywhere under nested tenant wrappers."""
    out: list[dict[str, Any]] = []
    if depth > 8 or not isinstance(obj, dict):
        return out
    groups = obj.get("groups")
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            gid = g.get("groupId") or g.get("group_id")
            plist = g.get("profiles")
            if isinstance(plist, list):
                for p in plist:
                    if not isinstance(p, dict):
                        continue
                    if "profileId" not in p and "profile_id" not in p:
                        continue
                    d = dict(p)
                    if gid is not None and d.get("groupId") is None:
                        d["groupId"] = str(gid)
                    out.append(d)
    for v in obj.values():
        if isinstance(v, dict):
            out.extend(_profiles_from_nested_groups(v, depth + 1))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for item in v:
                if isinstance(item, dict):
                    out.extend(_profiles_from_nested_groups(item, depth + 1))
    return out


def _dedupe_by_profile_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per profileId; merge groupId when the same athlete appears in multiple groups."""
    by_id: dict[str, dict[str, Any]] = {}
    for p in rows:
        pid = p.get("profileId") or p.get("profile_id")
        if pid is None:
            continue
        key = str(pid)
        if key not in by_id:
            by_id[key] = dict(p)
            continue
        cur = by_id[key]
        g_new = p.get("groupId") or p.get("group_id")
        g_old = cur.get("groupId") or cur.get("group_id")
        if g_new is not None:
            parts = []
            if g_old is not None:
                parts.extend(str(g_old).split(","))
            parts.extend(str(g_new).split(","))
            merged = ",".join(dict.fromkeys(s.strip() for s in parts if s.strip()))
            if merged:
                cur["groupId"] = merged
    return list(by_id.values())
