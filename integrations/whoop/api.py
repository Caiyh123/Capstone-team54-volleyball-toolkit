"""WHOOP Developer REST API (v2, /developer base). Pagination helpers."""
from __future__ import annotations

from typing import Any, Iterator

import requests

from integrations.whoop.oauth import WHOOP_API_BASE

DEFAULT_LIMIT = 25


def get_collection_page(
    path: str,
    *,
    access_token: str,
    limit: int = DEFAULT_LIMIT,
    start: str | None = None,
    end: str | None = None,
    next_token: str | None = None,
) -> dict[str, Any]:
    """GET one page; path like ``/v2/activity/sleep`` (no base URL)."""
    params: dict[str, Any] = {"limit": min(limit, 25)}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    if next_token:
        params["nextToken"] = next_token
    r = requests.get(
        f"{WHOOP_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params=params,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def iter_collection_records(
    path: str,
    *,
    access_token: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> Iterator[dict[str, Any]]:
    """Yield every record from a paginated ``records`` collection."""
    nt: str | None = None
    while True:
        data = get_collection_page(
            path,
            access_token=access_token,
            limit=limit,
            start=start if nt is None else None,
            end=end if nt is None else None,
            next_token=nt,
        )
        records = data.get("records")
        if not isinstance(records, list):
            break
        for rec in records:
            if isinstance(rec, dict):
                yield rec
        nt = data.get("next_token")
        if nt is None:
            nt = data.get("nextToken")
        if not nt:
            break
