# Requirements summary — Capstone Team 54 Volleyball Data Analysis Toolkit

## Goal

Build a **headless data pipeline** that ingests vendor performance data (Catapult, GymAware; later WHOOP, VALD, Teamworks where approved), stores it in **Supabase (Postgres)**, and supports **scheduled export→upload** plus **reporting / RCA** in **Power BI** (or similar). The system is **not** a live-streaming athlete app; routine refreshes are **automated**, not manual.

## In scope (current)

| Area | Requirement |
|------|-------------|
| **Catapult Connect** | Bulk export session metrics; upload to Postgres; optional load-index script. |
| **GymAware Cloud** | Export summaries (optional reps); upload to Postgres; **optional allowlist** filtering via workbook for roster/privacy scope. |
| **Verification** | `verify_integrations.py` confirms configured APIs respond. |
| **Scheduling** | Windows: `scripts/run_scheduled_sync.ps1` + Task Scheduler (see `docs/operations/runbook.md`). |
| **WHOOP (initial)** | FastAPI **Auth Bridge** (`backend/app.py`) + `schema/whoop_oauth_tokens.sql` + `integrations/whoop/oauth.py` — OAuth callback stores tokens; **nightly ETL** to metrics tables is a follow-up. |
| **Identity** | Schema for **athlete crosswalk** (`schema/athlete_identity.sql`); population is a separate data task with the client. |
| **Documentation** | Runbook, `.env.example`, integration notes under `docs/volley-etl/`. |

## Out of scope / deferred

| Area | Notes |
|------|--------|
| **WHOOP** | OAuth + refresh handling + ETL — planned; needs app registration and per-athlete consent flow. |
| **VALD** | Pending client API approval and regional credentials. |
| **Teamworks AMS** | Optional path; depends on tenant API access. |
| **Frontend** | Existing dashboard may be used for identity/OAuth only; core analytics are BI + DB. |

## Non-functional

- **Secrets** never committed (`.env` gitignored).
- **Exports / logs** local artifacts gitignored where listed in `.gitignore`.
- **Reproducible runs**: `requirements.txt`, Python 3.x, documented env vars.

## References

- Detailed integration scope: `docs/volley-etl/current_scope.md`
- Client credential checklist: `docs/volley-etl/client_integration_requirements.md`
- Operations: `docs/operations/runbook.md`
