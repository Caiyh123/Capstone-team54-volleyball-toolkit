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
   .\.venv\Scripts\python.exe verify_integrations.py
   ```

4. **Database** — run SQL in `schema/` (e.g. `catapult_session_metrics.sql`, `gymaware_summaries.sql`, `athlete_identity.sql`, `vald_profiles.sql`, `whoop_oauth_tokens.sql`) in the Supabase SQL editor as needed.

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

- Catapult: `bulk_export.py` → `upload_to_supabase.py`
- GymAware: `gymaware_export.py` → `upload_gymaware_to_supabase.py`
- Load index: `load_index.py`
- Integration smoke test: `verify_integrations.py`
- **VALD** (read API): `vald_export.py` — tenants + optional profiles; `upload_vald_profiles_to_supabase.py` — upsert into `vald_profiles`. Set `VALD_*` and `DATABASE_URL` in `.env`. See [`docs/volley-etl/vald_onboarding.md`](docs/volley-etl/vald_onboarding.md).
- **WHOOP Auth Bridge** (FastAPI): `backend/app.py` — run `uvicorn backend.app:app --reload --port 8000` from repo root after `pip install -r requirements.txt`. Apply `schema/whoop_oauth_tokens.sql` in Supabase. Set `WHOOP_*` and `DATABASE_URL` in `.env`. See `docs/volley-etl/end_to_end_workflow.md`.
- **Deploy bridge to Render:** `render.yaml` (Blueprint) + step-by-step guide: [`docs/operations/deploy-render-whoop-bridge.md`](docs/operations/deploy-render-whoop-bridge.md).

GymAware **allowlist** (workbook-driven athlete IDs): set `GYMAWARE_USE_ALLOWLIST=1` or use `python gymaware_export.py --allowlist`. See `docs/operations/runbook.md`.

## Documentation

- [Requirements summary](docs/requirements/requirements-summary.md)
- [Open questions](docs/requirements/open-questions.md)
- [Runbook](docs/operations/runbook.md)
- [VALD VA / ForceDecks entity notes](docs/volley-etl/vald_va_package_notes.md) (keys + future ForceDecks scope)

## Security

Do not commit `.env` or credentials. Use `.env.example` as the template only.
