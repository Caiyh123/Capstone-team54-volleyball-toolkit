# Product direction — scheduled ingestion & RCA (March 2026)

This document captures the pivot from **live streaming** to **periodic, hands-off data refresh**, plus **storytelling / root-cause** goals. Use it to align exports, Supabase uploads, scheduling, and BI/dashboard work.

---

## 1. Core pivot: live → scheduled uploads (not manual checks)

| Before (de-prioritized) | Now (priority) |
|-------------------------|----------------|
| Real-time live streaming | **Scheduled pipelines**: exports run on a **timer** (e.g. nightly/hourly), data is **pushed to Supabase** (and optional marts) **without the user triggering uploads**. |
| — | Users **open dashboard/BI** and see **already-fresh** layers — no expectation to “click compile” for routine updates. |

**Implication for engineering**

- Implement **repeatable jobs** (Windows Task Scheduler, `cron`, GitHub Actions, Azure Logic Apps, etc.) that call the existing scripts in order. Repo starter: **`scripts/run_scheduled_sync.ps1`** (Catapult + GymAware export→upload). Example:
  - Catapult: `bulk_export.py` → `upload_to_supabase.py`
  - GymAware: `gymaware_export.py` → `upload_gymaware_to_supabase.py`
  - Optional: `load_index.py` on an agreed cadence → persist result to DB or blob
- Jobs should be **idempotent** (upserts where possible) and **logged** (row counts, errors) so ops can verify runs without end-user action.
- **Optional later:** a **backfill** or **one-off** CLI for a specific session/date (historical correction) — **not** the primary UX for day-to-day freshness.
- **No requirement** for WebSocket/live sensor streaming for this phase.

---

## 2. Storytelling & root cause analysis (RCA)

**Goal:** Explain **why** performance changed — e.g. overlay **sleep / soreness** with **jump height** and load.

**Implication**

- Store and expose data with **shared dimensions**: at minimum **`athlete_internal_id`**, **`session_or_calendar_date`**, **`timestamp` or `day`** per source.
- **Master athlete mapping** (client-provided) is the **join key** across Catapult, GymAware, WHOOP, VALD, Teamworks AMS.
- Dashboard/BI layers need **toggleable series** (see below), not a single flat table.

---

## 3. Visualization & dashboard

| Requirement | Notes |
|-------------|--------|
| **Unified timeline** | One coherent time axis; overlay **all five sources** when credentials exist. |
| **Interactive toggles** | Turn layers **on/off** (sleep, soreness, jump metrics, load, VALD tests, etc.). |
| **Longitudinal** | **Week / month / season** views — trend engine, not only daily snapshot. |
| **BI tools** | Prefer **visual** exploration: **Power BI**, **Tableau**, or similar — star schema or wide **analytics views** fed from Supabase/warehouse. |

**Implication**

- Backend: **curated views** or **export marts** (e.g. `mart_athlete_day`, `mart_session_summary`) with consistent naming for BI.
- Frontend (Vercel) can stay for auth and light UX; **heavy viz** may live in **Power BI/Tableau** connected to the same DB or semantic layer.

---

## 4. Subjective wellness (Teamworks AMS)

| Field | Spec |
|--------|------|
| **Frequency** | Daily |
| **Scale** | Standardized **1–10** |
| **Metrics** | Physical **soreness**; **mental** and **physical** wellbeing |
| **Role** | **Context** for “hard” sensor data (load, jumps, etc.) |

**Implication**

- When AMS API access lands: land **`wellness_daily`** (or similar) with `athlete_internal_id`, `date`, metric keys, `score_1_10`, `source=teamworks_ams`.
- Correlate to Catapult **session date** and WHOOP **sleep/recovery** day boundaries in the **scheduled sync** or downstream **mart** build.

---

## 5. Technical status (snapshot)

| Item | Status |
|------|--------|
| **GymAware** | Account ID + token — **production-ready** integration path (export + DB). |
| **VALD** | Credentials **pending**. |
| **Teamworks AMS** | Credentials **pending**; wellness per spec above. |
| **Jump load** | **In repo**: `load_index.py` (+ R jump export `Jump Data - BEACH VB.R`). |
| **Spike tracking** | **Awaiting** Francois script — treat as **fifth narrative layer** when delivered. |
| **Athlete mapping** | Client **master list** — **required** for cross-source timeline and RCA. |

---

## 6. Suggested engineering backlog (ordered)

1. **Master athlete map** table + import process (client file → `athlete_external_ids`).
2. **Scheduled runner** — one script or orchestrator (e.g. `run_scheduled_sync.ps1` / `.sh` / CI workflow) that runs **Catapult + GymAware** export→upload on a schedule; extend with WHOOP/VALD/AMS when available.
3. **Schema / views for BI**: `athlete_day` grain (or session grain) for overlays; document **Power BI/Tableau** connection to Supabase/Postgres.
4. **WHOOP** (when OAuth/tokens): add steps to the same schedule — daily recovery/sleep into the same warehouse.
5. **VALD** + **Teamworks** when credentials arrive — same periodic pattern.
6. **Wire Francois spike** into the scheduled path or mart build.
7. *(Optional)* **Backfill** job: date/session scope for historical replays — secondary to scheduled freshness.

---

*Internal alignment doc — update as credentials and scripts land.*
