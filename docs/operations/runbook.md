# Operations runbook

## Environment

1. Clone the repository and open the repo root in your editor.
2. Copy `.env.example` to `.env` and fill secrets (never commit `.env`).
3. Create a virtual environment and install dependencies:

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, either call `python.exe` under `.venv\Scripts\` directly or run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

4. Smoke test:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_config.py
.\.venv\Scripts\python.exe verify_integrations.py
```

`preflight_config.py` reports which variables are set (no secrets). Apply SQL in the order in `schema/apply_order.txt` when bootstrapping Supabase.

Run Python from the **repository root** so `.env` and default paths (e.g. GymAware allowlist Excel) resolve correctly.

## Scheduled sync (Windows Task Scheduler)

The script `scripts/run_scheduled_sync.ps1` runs `python scheduled_etl.py --all --continue-on-error` from the repo root (all sources run; process exits non-zero if any step failed). That orchestrates, in order:

| Source | Scripts |
|--------|---------|
| Catapult | `bulk_export.py` → `upload_to_supabase.py` |
| GymAware | `gymaware_export.py` (rolling UTC window) → `upload_gymaware_to_supabase.py` |
| VALD | `upload_vald_profiles_to_supabase.py` + `upload_vald_forceframe_tests_to_supabase.py` + `upload_vald_forcedecks_to_supabase.py` (optional: `vald_export.py` manually for JSON snapshots) |
| WHOOP | `whoop_etl.py` |
| Catapult load index | `load_index.py` (rolling UTC window) → `upload_load_index_to_supabase.py` |

Run the same orchestrator on Linux/macOS with cron: `python scheduled_etl.py --all --continue-on-error` (use the venv’s `python` if applicable).

1. Set `GYMAWARE_USE_ALLOWLIST=1` in `.env` if exports must be limited to the allowlist workbook.
2. Place `GymAware API Reference Numbers.xlsx` (or set `GYMAWARE_ALLOWLIST_XLSX`) next to `.env` when allowlist is enabled.
3. Optional lookback env vars: `SCHEDULED_GYMAWARE_LOOKBACK_DAYS`, `SCHEDULED_WHOOP_LOOKBACK_DAYS`, `SCHEDULED_LOAD_INDEX_LOOKBACK_DAYS` (defaults 7 / 14 / 7).
4. Schedule **PowerShell** with execution policy bypass, pointing at this repo’s copy of the script:

```text
powershell.exe -ExecutionPolicy Bypass -File "D:\...\Capstone-team54-volleyball-toolkit\scripts\run_scheduled_sync.ps1"
```

5. Ensure **Python** is on the PATH used by the scheduled task, or edit the script to use a full path to `python.exe`.

Logs are written under `logs\` (gitignored).

Subset of sources only: `python scheduled_etl.py --sources catapult,gymaware`.

## Database schema

Use the full list in **`schema/apply_order.txt`** (Catapult base tables, optional Catapult views, load index tables, GymAware, VALD, WHOOP, `athlete_identity`). Applying only a subset will break uploads that target missing tables.

Summary:

- **Catapult:** `catapult_session_metrics.sql`, `catapult_stats_staging.sql`; optional `catapult_stats_staging_flat_view.sql`, `catapult_stats_bi_extract.sql` (BI scalar table filled by `upload_to_supabase.py`), `catapult_roster_from_stats_view.sql`; `catapult_load_index.sql` if you use load index uploads.
- **Other sources:** `gymaware_summaries.sql`, optional **`gymaware_extended.sql`** (reps/athletes/bests + BI extract), `vald_profiles.sql`, optional `vald_forceframe_tests_staging.sql` and `vald_forcedecks_*_staging.sql` if using those uploads, `whoop_oauth_tokens.sql`, `whoop_staging.sql`, optional **`whoop_bi_extract.sql`** (after medallion migration; flat WHOOP columns + triggers), `athlete_identity.sql` (roster crosswalk; populate separately).

## GitHub Actions and secrets

- Optional URL env vars (e.g. `CATAPULT_BASE_URL`) should be **unset** or omitted in GitHub Secrets if you want code defaults. An **empty** secret value overrides Python defaults and can produce invalid URLs.
- Raw staging tables are **append-only**: verify freshness with `ORDER BY etl_ingested_at DESC` or `MAX(etl_ingested_at)`, not only the first page of the Table Editor.

## Roster workbook (coaches edit Excel)

**Committed roster (online ETL):** `data/roster/roster_new.xlsx` in the GitHub repo. GitHub Actions sets `ROSTER_ALLOWLIST_XLSX=data/roster/roster_new.xlsx`; `scheduled_etl.py` syncs it to Supabase before vendor pulls. Coach handoff: see `data/roster/ROSTER_FOR_COACHES.md`.

**Local / manual sync** (optional if not running full scheduled ETL):

```powershell
python scripts/sync_roster_cohort_from_xlsx.py
python scripts/sync_athlete_identity_from_xlsx.py
```

- `roster_cohort` — cohort filtering for `*_roster` views and ETL allowlist (`ROSTER_FILTER=1`).
- `athlete_identity` — Global Athlete ID (`internal_key`, default `VB-{GymAware API ID}` unless a **Global Athlete ID** column is present) plus all vendor IDs for future Gold-layer joins.

## GymAware allowlist

When `GYMAWARE_USE_ALLOWLIST=1` (or `python gymaware_export.py --allowlist`), only rows whose `athleteReference` appears in the workbook are written to JSON and (for upload) sent to Postgres. Use `--no-allowlist` for a full export regardless of `.env`.

## GymAware `/bests` date chunks

`gymaware_export.py` splits long backfills for `GET /bests` into windows of **90 days** (under the API’s ~3-month limit per request). Summaries and reps still use **28-day** chunks. To use a different window (e.g. if GymAware changes limits or you want smaller requests), set **`GYMAWARE_BESTS_CHUNK_DAYS`** in `.env` before export.

## WHOOP Auth Bridge (FastAPI)

1. In Supabase, run `schema/whoop_oauth_tokens.sql`.
2. In the WHOOP Developer Dashboard, set the **Redirect URI** to your deployed callback, e.g. `https://<app>.onrender.com/callback` (must match `WHOOP_REDIRECT_URI` in `.env`).
3. From the **repository root**:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000
```

4. **Health:** `GET http://127.0.0.1:8000/health`
5. **Start OAuth:** open `http://127.0.0.1:8000/whoop/start?state=yourlabel12` (state must be **≥ 8 characters** per WHOOP). After consent, WHOOP redirects to `/callback` and tokens are stored if `DATABASE_URL` is set.

For production, deploy the same app to HTTPS (e.g. Render) and use the public URL in `WHOOP_REDIRECT_URI` and in the WHOOP dashboard.

**Full Render guide:** [deploy-render-whoop-bridge.md](./deploy-render-whoop-bridge.md) (includes `render.yaml` Blueprint).
