# Project status handover (Volleyball toolkit)

Snapshot for the team and client: what is working, how to run it, silver read models for the website, and what remains. Repository: **Capstone-team54-volleyball-toolkit**.

---

## Completed (working end-to-end)

### Infrastructure

- **Supabase (Postgres):** Schema under `schema/` — apply order in `schema/apply_order.txt`.
- **Medallion raw layer:** Append-only staging/BI with `etl_ingested_at` / `ingest_id` (`schema/medallion_raw_layer_migration.sql`).
- **Environment:** Copy `.env.example` to `.env` (never commit `.env`). Offline check: `python scripts/preflight_config.py`.
- **CI:** `.github/workflows/ci.yml` (compile check); `.github/workflows/daily_etl.yml` (nightly multi-source ETL + roster sync).

### Roster and athlete identity (automated)

- **Coach workbook:** `data/roster/roster_new.xlsx` (committed for GitHub Actions). Instructions: `data/roster/README.md`, `data/roster/ROSTER_FOR_COACHES.md`.
- **Sync scripts:** `scripts/sync_athlete_identity_from_xlsx.py`, `scripts/sync_roster_cohort_from_xlsx.py`.
- **`scheduled_etl.py`:** Runs roster sync before vendor ETL unless `SCHEDULED_SKIP_ROSTER_SYNC=1`.
- **`public.athlete_identity`:** Crosswalk (`internal_key`, Catapult/GymAware/VALD/WHOOP IDs, display names). Populated from workbook sync.

### Catapult

- **Export/load:** `bulk_export.py` → `upload_to_supabase.py` → `catapult_stats_staging` + `catapult_stats_bi_extract`.
- **Silver (reporting):** `schema/silver_catapult_session.sql` → `silver_catapult_session` — one row per player per session (deduped ingests; periods aggregated). **Gold daily rollup deferred** per client (session-level reporting). See `docs/volley-etl/catapult_medallion_layers.md`.
- **Load index:** `load_index.py` → `upload_load_index_to_supabase.py`.

### GymAware (extended)

- **Export:** `gymaware_export.py` — `/summaries`, `/reps`, `/athletes`, `/bests` (bests chunked; `GYMAWARE_BESTS_CHUNK_DAYS`, default 90).
- **Load:** `upload_gymaware_to_supabase.py` → staging + BI extract tables (`schema/gymaware_extended.sql`).
- **Silver:** `schema/silver_gymaware.sql` — summaries, reps, bests, athletes with `athlete_internal_key` / `athlete_display_name`.

### WHOOP

- **Auth bridge:** `backend/app.py` — OAuth start/callback; tokens in `whoop_oauth_token`.
- **ETL:** `whoop_etl.py` → staging + `whoop_*_bi_extract` (with `whoop_bi_extract.sql`).
- **Silver:** `schema/silver_whoop.sql` — cycle, sleep, workout, recovery, `silver_whoop_sleep_longest_per_day`.

### VALD

- Profiles + optional ForceFrame / ForceDecks staging uploads via `scheduled_etl.py`. See `docs/volley-etl/vald_onboarding.md`.

### Scheduled pipeline

- **`scheduled_etl.py`:** Roster sync → Catapult → GymAware → VALD → WHOOP → load index (+ DB upload). Non-zero exit if any step failed.
- **Windows:** `scripts/run_scheduled_sync.ps1`.
- **GitHub Actions:** `daily_etl.yml` with `ROSTER_ALLOWLIST_XLSX=data/roster/roster_new.xlsx`, `ROSTER_FILTER=1`.

### Analytics read model (VPA website / BI)

- **VPA app (separate repo):** FastAPI + React dashboard reads silver tables via PostgREST (`SUPABASE_SERVICE_KEY`). See `docs/operations/vpa_frontend_integration.md`.
- **Do not report from raw `*_bi_extract`** — duplicate rows from append-only ingests.
- **Use silver views** + `athlete_identity`. Cross-source pattern: `docs/volley-etl/cross_source_correlation.md`.
- **Legacy dashboard tables removed:** `cleanup_legacy_dashboard.sql`.

### Documentation

| Document | Purpose |
|----------|---------|
| `docs/design/system_design.md` | Architecture, workflows, design decisions |
| `docs/operations/web_app_handover.md` | Silver contract for VPA |
| `docs/operations/vpa_frontend_integration.md` | VPA ↔ ETL two-repo setup |
| `docs/operations/testing_notes.md` | Smoke tests, ETL verification, known issues |
| `docs/operations/product_review_checklist.md` | Rubric alignment for capstone review |
| `docs/data_dictionary_baseline.md` | Column-level reference |
| `docs/volley-etl/cross_source_correlation.md` | Athlete + date correlation across sources |

---

## Verified in practice

- `scheduled_etl.py --all` — Catapult, GymAware, VALD profiles, WHOOP ETL, load index (when credentials set).
- Silver views applied in dev Supabase; row counts deduped vs bronze (e.g. Catapult 146 bronze rows → 65 session rows; WHOOP recovery deduped to one row per cycle).
- Roster-linked athletes show `athlete_display_name` on silver WHOOP/Catapult/GymAware where IDs are filled in `roster_new.xlsx`.

---

## Remaining / post-review (optional)

| Area | Notes |
|------|--------|
| **VPA frontend** | Built in separate `vpa/` repo (React + FastAPI); consumes silver tables documented in `vpa_frontend_integration.md`. This repo’s `frontend/` remains unused. |
| **VPA `/vald` page** | Placeholder only in VPA; VALD ETL/staging exists in this repo; `silver_vald_*` not built. |
| **RLS & API layer** | Tables unrestricted until RLS or backend API with service role. |
| **WHOOP athlete onboarding** | Only roster athletes with `whoop_user_id` + completed OAuth receive data. |
| **Catapult rate limits (429)** | Bulk export may need backoff/tuning under heavy CI runs. |
| **Gold Catapult daily rollup** | Not built — client wants independent sessions. |
| **Teamworks AMS** | Placeholder only. |
| **Power BI** | Deprioritized in favour of custom web; silver schema unchanged for either consumer. |

---

## Quick commands (repo root)

```text
python scripts/preflight_config.py
python verify_integrations.py
python scheduled_etl.py --all
python scripts/sync_athlete_identity_from_xlsx.py
```

---

## Key files

| Path | Role |
|------|------|
| `schema/silver_*.sql` | Reporting views (apply after BI extract DDL) |
| `data/roster/roster_new.xlsx` | Coach-maintained roster |
| `scheduled_etl.py` | Multi-source scheduler |
| `docs/operations/runbook.md` | Install + scheduling |
| `docs/operations/product_review_checklist.md` | Assessment rubric checklist |
