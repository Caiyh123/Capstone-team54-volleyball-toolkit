# Requirements summary — Capstone Team 54 Volleyball Data Analysis Toolkit

## Goal

Build a **headless data pipeline** that ingests vendor performance data (Catapult, GymAware, WHOOP, VALD; Teamworks when approved), stores it in **Supabase (Postgres)**, and supports **scheduled export→upload** plus **silver read models** for a **custom analytics website** (Power BI optional). Routine refreshes are **automated**, not manual.

## In scope (current)

| Area | Requirement |
|------|-------------|
| **Catapult Connect** | Bulk export session metrics; upload to Postgres; optional load-index script. |
| **GymAware Cloud** | Export summaries (optional reps); upload to Postgres; **optional allowlist** filtering via workbook for roster/privacy scope. |
| **Verification** | `verify_integrations.py` confirms configured APIs respond. |
| **Scheduling** | Windows: `scripts/run_scheduled_sync.ps1` + Task Scheduler (see `docs/operations/runbook.md`). |
| **WHOOP** | Auth Bridge + nightly ETL + `whoop_bi_extract` + `silver_whoop_*` views. |
| **Identity** | `athlete_identity` + `roster_new.xlsx` sync (automated in `scheduled_etl.py`). |
| **Silver layer** | Deduped views for Catapult sessions, WHOOP, GymAware (`schema/silver_*.sql`). |
| **Documentation** | Runbook, `.env.example`, integration notes under `docs/volley-etl/`. |

## Out of scope / deferred

| Area | Notes |
|------|--------|
| **Teamworks AMS** | Optional path; depends on tenant API access. |
| **Frontend website** | In progress; consumes silver views per `docs/operations/web_app_handover.md`. |
| **RLS / production API** | Documented; implementation deferred. |
| **Catapult Gold (daily rollup)** | Deferred — client wants session-level reporting. |

## Non-functional

- **Secrets** never committed (`.env` gitignored).
- **Exports / logs** local artifacts gitignored where listed in `.gitignore`.
- **Reproducible runs**: `requirements.txt`, Python 3.x, documented env vars.

## References

- Detailed integration scope: `docs/volley-etl/current_scope.md`
- Client credential checklist: `docs/volley-etl/client_integration_requirements.md`
- Operations: `docs/operations/runbook.md`
