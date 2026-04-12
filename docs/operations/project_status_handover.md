# Project status handover (Volleyball toolkit)

Snapshot for the team: what is working in the repo, how to run it, and what remains. Repository: **Capstone-team54-volleyball-toolkit**.

---

## Completed (working end-to-end)

### Infrastructure

- **Supabase (Postgres):** Schema files under `schema/` — apply order in `schema/apply_order.txt`.
- **Environment:** Copy `.env.example` to `.env` (never commit `.env`). Offline check: `python scripts/preflight_config.py` (prints yes/no only).
- **CI:** GitHub Actions runs `python -m compileall` on push/PR (`.github/workflows/ci.yml`).

### Catapult

- **Export:** `bulk_export.py` — pulls recent activities and stats → `catapult_bulk_export.json`.
- **Load:** `upload_to_supabase.py` — **upserts** full `POST /stats` rows into `public.catapult_stats_staging` (`stats_payload` JSONB); still **inserts** narrow metrics into `public.catapult_session_metrics` (legacy). Apply `schema/catapult_stats_staging.sql` in Supabase.
- **Load index (metric):** `load_index.py` — strain/jump-based load index → `load_index_result.json` (file output; not all metrics are uploaded to a dedicated table unless extended).

### GymAware

- **Export:** `gymaware_export.py` — date-range summaries (optional reps) → JSON.
- **Load:** `upload_gymaware_to_supabase.py` — upserts into `public.gymaware_summaries`.
- **Allowlist:** Optional workbook filter for privacy (`integrations/gymaware/allowlist.py`, env + flags).

### VALD

- **Client:** `integrations/vald/client.py` — OAuth client credentials, tenants/profiles.
- **Load:** `upload_vald_profiles_to_supabase.py` — upserts into `public.vald_profiles`.
- **Smoke/export:** `vald_export.py`.

### WHOOP (direct Developer API)

- **Auth bridge (FastAPI):** `backend/app.py` — `/whoop/start`, `/callback`, `/health`, `/whoop/oauth-check`. Deploy with `uvicorn` (see `render.yaml` / `docs/operations/deploy-render-whoop-bridge.md`).
- **OAuth:** `integrations/whoop/oauth.py` — authorization code + **refresh token** (`client_secret_post`). REST base: `https://api.prod.whoop.com/developer` (not the same path as `/oauth/`).
- **Tokens:** Stored in `public.whoop_oauth_token` when `DATABASE_URL` is set.
- **ETL:** `whoop_etl.py` — refreshes tokens, pulls sleep / workout / cycle / recovery into staging tables (`whoop_*_staging`, audit `whoop_etl_run`). See `schema/whoop_staging.sql`.

### Scheduled multi-source pipeline

- **Orchestrator:** `scheduled_etl.py` — runs Catapult → GymAware → VALD profiles → WHOOP ETL → Catapult `load_index` (or subsets via `--sources`).
- **Windows Task Scheduler:** `scripts/run_scheduled_sync.ps1` calls `scheduled_etl.py --all`; logs under `logs/`.
- **Docs:** `docs/operations/runbook.md`, README “Main Python entrypoints”.

### Identity (schema only)

- **`public.athlete_identity`:** DDL in `schema/athlete_identity.sql` — crosswalk for roster ↔ Catapult / GymAware / VALD / WHOOP / Teamworks. **Population** is a process task (spreadsheet/import), not automated in repo.

---

## Verified in practice (recent run)

- `scheduled_etl.py --all` completed successfully: Catapult upload, GymAware upload, VALD profiles upsert, WHOOP ETL (no API error), load index JSON written.
- **New WHOOP accounts** may return **zero** rows until there is scored sleep/activity in the requested lookback window — expected, not a pipeline failure.

---

## Remaining / next steps for the team

| Area | Notes |
|------|--------|
| **Master roster → `athlete_identity`** | Import client roster; fill `internal_key`, vendor IDs (`whoop_user_id`, `vald_profile_id`, etc.). Enables personalized WHOOP links (`/whoop/start?state=...`) and BI joins. |
| **WHOOP data volume** | Re-run `whoop_etl.py` after athletes have nights/activities; tune `--lookback-days` if needed. |
| **RLS & security** | Tables are **UNRESTRICTED** in Supabase until RLS (or restricted roles) is applied — especially token and PII tables. |
| **Production hosting** | Render (or other) for the Auth Bridge; ensure `WHOOP_REDIRECT_URI` matches dashboard + env. Scheduler can run on any machine/cron with `.env`. |
| **Teamworks AMS** | Config placeholders only — no ETL script until API access and requirements are clear (`docs/volley-etl/whoop_via_teamworks.md`). |
| **VALD ForceDecks / product metrics** | Profiles are in; ForceDecks and other products are follow-up (see `docs/volley-etl/vald_va_package_notes.md`). |
| **BI / dashboards** | Wire Supabase to Power BI or stack of choice; staging JSONB may need views or flattened tables for reporting. |
| **Documentation polish** | Central `docs/volley-etl/current_scope.md` may predate WHOOP/VALD delivery — align narrative when convenient. |

---

## Quick commands (repo root)

```text
python scripts/preflight_config.py
python verify_integrations.py
python scheduled_etl.py --all
python scheduled_etl.py --sources catapult,gymaware
```

---

## Key files

| Path | Role |
|------|------|
| `.env.example` | Variable reference |
| `schema/apply_order.txt` | Supabase DDL order |
| `scheduled_etl.py` | Multi-source scheduler |
| `whoop_etl.py` | WHOOP-only ETL |
| `backend/app.py` | WHOOP OAuth bridge |
| `docs/operations/runbook.md` | Install + Task Scheduler |
| `docs/operations/deploy-render-whoop-bridge.md` | Render deploy |
