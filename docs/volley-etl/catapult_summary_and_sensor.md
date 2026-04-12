# Catapult Connect v6 — summary stats vs 10 Hz sensor (for DB expansion)

Verified against live API (`CATAPULT_BASE_URL` + `CATAPULT_TOKEN`). Re-run introspection anytime:

```bash
python scripts/catapult_discover.py --write-json
```

## 1. Summary data (`POST /stats`)

- **Endpoint:** `POST {base}/stats`
- **Typical body:** `group_by: ["participating_athlete"]`, `filters: [{ name: "activity_id", comparison: "=", values: [<uuid>] }]`
- **Returns:** one row per participating athlete for that activity, with **many** numeric/text metric fields (hundreds of keys on typical tenants): distance, player load, velocity bands, IMA counts, heart-rate bands, metabolic power, sport-specific columns, etc.
- **What we persist today:** only `total_distance`, `total_player_load`, `field_time`, plus `activity_id` / `athlete_id` in `public.catapult_session_metrics` (see `upload_to_supabase.py`).
- **Database expansion options:**
  - **Recommended:** new table e.g. `catapult_stats_staging` with `(activity_id, athlete_id)` unique and **`stats_payload JSONB`** storing the full stats row, plus `synced_at`. Lets you add indexes/views later without 400 columns.
  - **Alternative:** curated subset of metrics as real columns for BI (higher maintenance).

## 2. Sensor data — 10 Hz (`GET .../sensor`)

- **Endpoint:** `GET {base}/activities/{activity_id}/athletes/{athlete_id}/sensor`
- **Returns:** JSON array (usually one element) with metadata and `data`: array of ~10 Hz samples.
- **Sample column set (live):** `ts`, `cs`, `lat`, `long`, `o`, `v`, `a`, `hr`, `pl`, `mp`, `sl`, `x`, `y` (meanings align with Catapult’s public catapultR docs: time, lat/long, odometer, velocity, acceleration, HR, player load, metabolic power, smoothed load, field x/y).
- **Volume:** one athlete-activity can be **multi‑MB** JSON (tens of thousands of rows). Not suitable as a single unbounded Postgres row for every sync.
- **Database expansion options:**
  - **Recommended:** store **files** (Parquet/CSV) in object storage with a **manifest table** in Postgres: `activity_id`, `athlete_id`, `storage_url`, `row_count`, `synced_at`, `stream_type`.
  - **Optional:** downsampled or session-level aggregates only in Postgres.
  - **Full 10 Hz in Postgres:** only if you partition aggressively and accept retention limits—usually overkill for analytics.

## 3. CatapultR scope

- **CatapultR** is an **R client** to the same cloud APIs; it does not add new REST endpoints. Use it for exploration or parity checks; production ETL can stay Python.

## 4. Related scripts in repo

| Script | Purpose |
|--------|---------|
| `bulk_export.py` | Last N activities → `POST /stats` per activity → `catapult_bulk_export.json` |
| `upload_to_supabase.py` | Narrow insert into `catapult_session_metrics` |
| `get_session_data.py` | Print sample keys from `/stats` for one activity |
| `load_index.py` | Uses `/stats` + `/activities/{id}/athletes` + `/events` for load index |
| `scripts/catapult_discover.py` | Key counts + 10 Hz column names + tiny sample |
