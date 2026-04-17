# Capstone Team 54 — Volleyball Data Analysis Toolkit

Headless ETL pipeline: **Catapult** and **GymAware** → **Supabase (Postgres)** for analytics (e.g. Power BI). Optional sources (WHOOP, VALD, Teamworks) are documented under `docs/volley-etl/`.

## Quick start

1. **Clone** and open the repository root.
2. **Environment**
   - Copy `.env.example` to `.env` and fill in values (never commit `.env`).
   - Create a venv and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   If PowerShell blocks script activation, use `.\.venv\Scripts\python.exe` for all commands, or set execution policy: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`.

3. **Verify** connectivity:

   ```powershell
   .\.venv\Scripts\python.exe scripts\preflight_config.py
   .\.venv\Scripts\python.exe verify_integrations.py
   ```

   `preflight_config.py` only reports which env vars are set (no secrets). `verify_integrations.py` calls Catapult/GymAware (and VALD if configured).

4. **Database** — run SQL in `schema/` in the Supabase SQL editor. Suggested order: `schema/apply_order.txt`.

## Repository layout

| Path | Purpose |
|------|---------|
| `integrations/` | Shared config; GymAware, WHOOP, VALD clients |
| `schema/` | Postgres DDL for Supabase |
| `scripts/` | Scheduled sync (`run_scheduled_sync.ps1`), R helper |
| `docs/requirements/` | Capstone requirements and open questions |
| `docs/volley-etl/` | Integration scope, client checklists, WHOOP/VALD notes |
| `docs/operations/runbook.md` | Install, scheduling, allowlist behavior |
| `backend/`, `frontend/` | Reserved for future app surfaces |

## Main Python entrypoints

- Catapult: `bulk_export.py` → `upload_to_supabase.py` (full stats JSONB in `catapult_stats_staging` + narrow `catapult_session_metrics`; apply `schema/catapult_stats_staging.sql`). For production roster scope set **`ROSTER_FILTER=1`** in `.env` so export and upload only include athletes in the workbook (otherwise all sessions’ athletes can be ingested). SQL cohort views: `schema/roster_filtered_views.sql` (`catapult_stats_staging_roster`), then optional `catapult_stats_staging_flat_view.sql`, `catapult_roster_from_stats_view.sql`. Export cap: `CATAPULT_BULK_EXPORT_LIMIT` or `bulk_export.py --all`.
- Load index: `load_index.py` → `upload_load_index_to_supabase.py` (apply `schema/catapult_load_index.sql`; JSON then DB run + per-activity rows)
- GymAware: `gymaware_export.py` → `upload_gymaware_to_supabase.py`
- Integration smoke test: `verify_integrations.py`
- **VALD** (read API): `vald_export.py` — tenants + optional profiles; `upload_vald_profiles_to_supabase.py` — upsert into `vald_profiles`. Set `VALD_*` and `DATABASE_URL` in `.env`. See [`docs/volley-etl/vald_onboarding.md`](docs/volley-etl/vald_onboarding.md).
- **WHOOP Auth Bridge** (FastAPI): `backend/app.py` — run `uvicorn backend.app:app --reload --port 8000` from repo root after `pip install -r requirements.txt`. Apply `schema/whoop_oauth_tokens.sql` in Supabase. Set `WHOOP_*` and `DATABASE_URL` in `.env`. See `docs/volley-etl/end_to_end_workflow.md`.
- **WHOOP ETL** (scheduled job): `whoop_etl.py` — refresh tokens and append sleep/workout/cycle/recovery into staging tables. Requires `schema/whoop_staging.sql`, `schema/medallion_raw_layer_migration.sql`, linked rows in `whoop_oauth_token`, and the same `WHOOP_CLIENT_*` + `DATABASE_URL` as the bridge.
- **All sources (scheduler):** `scheduled_etl.py` — runs Catapult, GymAware, VALD profile upload, WHOOP ETL, and Catapult load index + DB upload in one pipeline (`--all` or `--sources ...`). See `docs/operations/runbook.md` and `scripts/run_scheduled_sync.ps1`.
- **Deploy bridge to Render:** `render.yaml` (Blueprint) + step-by-step guide: [`docs/operations/deploy-render-whoop-bridge.md`](docs/operations/deploy-render-whoop-bridge.md).

GymAware **allowlist** (workbook-driven athlete IDs): set `GYMAWARE_USE_ALLOWLIST=1` or use `python gymaware_export.py --allowlist`. See `docs/operations/runbook.md`.

## Documentation

- **[Team handover: what works / what’s next](docs/operations/project_status_handover.md)**
- [Requirements summary](docs/requirements/requirements-summary.md)
- [Open questions](docs/requirements/open-questions.md)
- [Runbook](docs/operations/runbook.md)
- [VALD VA / ForceDecks entity notes](docs/volley-etl/vald_va_package_notes.md) (keys + future ForceDecks scope)
- [Catapult summary vs 10 Hz sensor](docs/volley-etl/catapult_summary_and_sensor.md) — `python scripts/catapult_discover.py`

## Security

Do not commit `.env` or credentials. Use `.env.example` as the template only.
