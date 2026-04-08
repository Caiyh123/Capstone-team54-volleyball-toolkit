"""
GymAware Cloud API client.

Auth: HTTP Basic — username = Account ID, password = API token (not Bearer).
Responses: newline-separated JSON objects (NDJSON stream).

Docs:
  https://gymaware.com/gymaware-cloud-api-integration-guide/
  https://gymaware.zendesk.com/hc/en-us/articles/360001396875-API-Integration
Example app: https://bitbucket.org/KineticPerformance/gymawareapi/src/master/
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

from integrations import config


def parse_ndjson_stream(text: str) -> list[dict[str, Any]]:
    """GymAware GET endpoints return a newline-separated stream of JSON objects."""
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _single_json_or_stream(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    if "\n" in text:
        return parse_ndjson_stream(text)
    return json.loads(text)


class GymAwareClient:
    """
    Base URL defaults to https://cloud.gymaware.com/api per official guide.
    Set GYMAWARE_ACCOUNT_ID and GYMAWARE_TOKEN in .env.
    """

    def __init__(
        self,
        account_id: str | None = None,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("GYMAWARE_BASE_URL", "https://cloud.gymaware.com/api")
        ).rstrip("/")
        self._account_id = account_id or config.gymaware_account_id()
        self._token = token or config.gymaware_token()
        self._auth = (self._account_id, self._token)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        r = requests.get(
            url,
            auth=self._auth,
            params=params or {},
            headers={"Accept": "application/json"},
            timeout=120,
        )
        r.raise_for_status()
        return _single_json_or_stream(r.text)

    def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        r = requests.post(
            url,
            auth=self._auth,
            json=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=120,
        )
        r.raise_for_status()
        text = r.text.strip()
        if not text:
            return None
        return json.loads(text)

    def refresh(self) -> dict[str, Any]:
        """
        POST /refresh — invalidates the current token and returns a new one.
        Subsequent calls use the new token automatically.
        """
        data = self._post("/refresh")
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected /refresh response")
        new_token = data.get("token")
        account_id = data.get("accountID") or self._account_id
        if new_token:
            self._token = new_token
            self._account_id = str(account_id)
            self._auth = (self._account_id, self._token)
        return data

    def list_staff(self) -> list[dict[str, Any]]:
        raw = self._get("/staff")
        return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])

    def list_athletes(self) -> list[dict[str, Any]]:
        raw = self._get("/athletes")
        return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])

    def list_summaries(
        self,
        *,
        start: float | None = None,
        end: float | None = None,
        modified_since: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        if modified_since is not None:
            params["modifiedSince"] = modified_since
        raw = self._get("/summaries", params=params if params else None)
        return raw if isinstance(raw, list) else ([] if raw is None else [raw])  # type: ignore[list-item]

    def list_reps(
        self,
        *,
        start: float | None = None,
        end: float | None = None,
        modified_since: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        if modified_since is not None:
            params["modifiedSince"] = modified_since
        raw = self._get("/reps", params=params if params else None)
        return raw if isinstance(raw, list) else ([] if raw is None else [raw])  # type: ignore[list-item]

    def list_analysis_types(self) -> list[dict[str, Any]]:
        raw = self._get("/analysis")
        return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])

    def list_exercises(self) -> list[dict[str, Any]]:
        raw = self._get("/exercises")
        return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])

    def list_activity_definitions(self) -> list[dict[str, Any]]:
        """Activities (Jump, Olympic, etc.) — every set belongs to one activity."""
        raw = self._get("/activities")
        return raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])


def test_athlete_sport_lookup(
    summaries_path: str | None = None,
    athlete_reference: str | int | None = None,
) -> None:
    """
    TEMPORARY: Option B — verify GET /athletes/{athleteReference} and whether `sport` is present.

    Picks athleteReference from gymaware_summaries_export.json unless overridden.
    Prints HTTP status and raw body (does not raise on non-2xx).
    """
    import sys

    root = os.getenv("VOLLEY_ROOT", os.getcwd())
    path = summaries_path or os.path.join(root, "gymaware_summaries_export.json")
    if athlete_reference is None:
        if not os.path.isfile(path):
            print(f"[ERROR] No summaries file at {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        if not rows or not isinstance(rows, list):
            print("[ERROR] Export must be a non-empty JSON array")
            sys.exit(1)
        ref = None
        for row in rows:
            if isinstance(row, dict) and row.get("athleteReference") is not None:
                ref = row["athleteReference"]
                break
        if ref is None:
            print("[ERROR] No athleteReference in export")
            sys.exit(1)
        athlete_reference = ref

    client = GymAwareClient()
    url = f"{client.base_url}/athletes/{athlete_reference}"
    print(f"[INFO] GET {url}")
    print(f"[INFO] athleteReference={athlete_reference!r}")

    r = requests.get(
        url,
        auth=client._auth,
        headers={"Accept": "application/json"},
        timeout=120,
    )
    print(f"[INFO] HTTP {r.status_code}")
    print("[INFO] Raw response body:")
    print(r.text)

    if r.ok:
        try:
            data = r.json()
            print("\n[INFO] Parsed JSON keys:", list(data.keys()) if isinstance(data, dict) else type(data))
            if isinstance(data, dict):
                sport = data.get("sport")
                print(f"[INFO] sport field: {sport!r}")
        except json.JSONDecodeError:
            print("[WARN] Body is not JSON")
    else:
        print("\n[INFO] Fallback: GET /athletes (full list) and find matching athleteReference...")
        try:
            all_a = client.list_athletes()
            match = next(
                (
                    a
                    for a in all_a
                    if isinstance(a, dict)
                    and str(a.get("athleteReference")) == str(athlete_reference)
                ),
                None,
            )
            if match is None:
                print("[WARN] No matching athlete in list_athletes()")
            else:
                print("[INFO] Match from list_athletes — raw record:")
                print(json.dumps(match, indent=2))
                print(f"[INFO] sport field: {match.get('sport')!r}")
        except Exception as e:
            print(f"[WARN] Fallback failed: {e}")


def _smoke() -> None:
    try:
        c = GymAwareClient()
    except RuntimeError as e:
        print(
            "[HINT] Set GYMAWARE_ACCOUNT_ID and GYMAWARE_TOKEN in .env "
            "(GymAware Cloud > Settings > Tokens).",
        )
        raise SystemExit(str(e)) from e
    athletes = c.list_athletes()
    print(f"[OK] GymAware: retrieved {len(athletes)} athlete record(s) (NDJSON rows).")
    if athletes:
        a0 = athletes[0]
        ref = a0.get("athleteReference") or ""
        ref_s = f"{ref[:8]}..." if len(ref) > 8 else ref
        name = a0.get("displayName") or f"{a0.get('firstName', '')} {a0.get('lastName', '')}".strip()
        print(f"     Sample: {name} (ref={ref_s})")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test-sport":
        test_athlete_sport_lookup()
    else:
        _smoke()
