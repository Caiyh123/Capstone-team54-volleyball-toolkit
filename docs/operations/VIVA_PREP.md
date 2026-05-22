# Viva prep — technical Q&A, code walkthrough, product review

**Personal study guide** (plain language). Keep this open during Zoom prep; do not read it word-for-word in the viva — use it to rehearse answers in your own words.

**Repo:** `Capstone-team54-volleyball-toolkit` · **Latest data commit:** `b37efe2` (silver + docs)

---

## Part 0 — Your 30-second opening (memorize)

> “I built the **data platform** for the volleyball team: automated pipelines that pull Catapult, GymAware, WHOOP, and VALD into **Supabase**, keep a **coach roster** in sync, and expose **silver views** so the website can show one athlete on one date across sources. I did not build the React frontend — my deliverable is the **database + ETL + documentation** the website plugs into.”

Then offer to screen-share: GitHub → one Python file → Supabase silver query.

---

## Part 1 — Product review requirements (what assessors want)

You must pass **all four** areas (≥50% each). Use this table to check you can speak to each.

| Rubric area | Weight | What to show | Your evidence |
|-------------|--------|--------------|---------------|
| **Individual contribution** | 40% | Tasks you personally did; complexity; git proof | Commits as `potsy017`; silver SQL, roster CI, GymAware extended, medallion docs, `scheduled_etl` roster sync |
| **Technical understanding** | 40% | Explain *why*, not only *what* | This doc §3–4; `docs/design/system_design.md` |
| **Product quality & client alignment** | 40% | Works for client; professional | Nightly ETL, session-level Catapult, unified athlete names; honest: website UI = other track |
| **Supporting documentation** | 20% | Design doc, git, tests | `system_design.md`, `testing_notes.md`, `product_review_checklist.md`, pushed to GitHub |

### CLOs (course outcomes) — one sentence each

| CLO | Say this |
|-----|----------|
| **CLO1** PM + quality | We used a medallion pipeline, GitHub Actions for nightly runs, and a runbook so ops are repeatable. |
| **CLO2** Team | I owned backend data; teammates own frontend; we share `athlete_identity` and silver table names. |
| **CLO3** Client alignment | Client wanted **session-level** Catapult and a **custom site** instead of Power BI — silver views are the contract for that. |
| **CLO4** Reflection | Hardest lessons: duplicate ingests in append-only bronze, WHOOP OAuth per athlete, GymAware API chunking. |
| **CLO5** Ethics | Roster filter limits who we ingest; WHOOP is health data — we documented RLS for production. |
| **CLO6** Handover | `project_status_handover.md`, `web_app_handover.md`, data dictionary, this repo on GitHub. |

### Logistics checklist (day of)

- [ ] Zoom open, screen share ready
- [ ] GitHub `main` branch open (show `b37efe2` and your older commits)
- [ ] Supabase SQL Editor — test query ready (below)
- [ ] Optional: GitHub Actions → Daily ETL → last green run
- [ ] Backlog / journal open (must match what you claim)
- [ ] Do **not** blame frontend team — say “data contract is ready; UI is in progress”

---

## Part 2 — Technical Q&A (likely questions + answers)

Read the **Short answer** first; use **If they push** only if asked to go deeper.

---

### Big picture

**Q: What does the system do?**  
**Short:** Vendors have separate apps. We pull their APIs on a schedule, store everything in Postgres (Supabase), map athletes through one roster file, and expose clean **silver** tables for the website.  
**If they push:** Not live streaming — batch ETL once per night (or manual run). Coaches edit Excel; code syncs IDs to the database.

**Q: Why Supabase / Postgres instead of Excel or Power BI only?**  
**Short:** One central database, automated refresh, and SQL views the web app can query. Power BI was the original plan; client moved to a **custom website** — same data, different UI.

**Q: What is your personal scope vs the team?**  
**Short:** ETL orchestration, roster sync, bronze/silver schema, GymAware extended endpoints, WHOOP silver dedup, documentation, GitHub Actions alignment. Frontend is separate.

---

### Bronze / Silver / Gold

**Q: What is bronze, silver, and gold?**  
**Short:**  
- **Bronze** = raw loads every run (append-only; duplicates possible).  
- **Silver** = cleaned views: one row per real-world thing (one session, one WHOOP cycle).  
- **Gold** = daily rollups — **we did not build Catapult Gold** because the client wants **each training session separate**, not one row per athlete per day.

**Q: Why append-only bronze instead of updating rows?**  
**Short:** Simpler and safer ETL — every run is auditable. We never overwrite vendor JSON by mistake. Dashboards use **silver**, not raw bronze.

**Q: Why did Catapult numbers look wrong in Power BI before?**  
**Short:** Bronze had **3–6 duplicate rows** per session from re-ingesting the same API data. Summing those inflated totals. **Silver** keeps the latest ingest per session key.

**Q: Why don’t WHOOP, Catapult, and GymAware have the same row count on one day?**  
**Short:** Different **grain**. WHOOP ≈ one recovery per cycle; Catapult = 0–many **sessions**; GymAware = many **sets/reps**. We correlate by **athlete name + date**, not matching row counts. See `docs/volley-etl/cross_source_correlation.md`.

---

### Roster and athlete identity

**Q: How do you know the same person across Catapult, WHOOP, and GymAware?**  
**Short:** `data/roster/roster_new.xlsx` has columns for each vendor ID. Scripts upsert into `athlete_identity`. Silver views join that table to add `athlete_display_name`.

**Q: Why is the roster in GitHub?**  
**Short:** GitHub Actions runs ETL without a coach logging into a server. Committed workbook + nightly sync keeps CI and production aligned.

**Q: What is `ROSTER_FILTER=1`?**  
**Short:** Only athletes on the roster are exported/ingested — privacy and scope control for the squad.

**Q: What is `internal_key`?**  
**Short:** Our stable ID (e.g. `VB-12345` from GymAware reference). Website and joins use it so we don’t rely on display names alone.

---

### WHOOP

**Q: How does WHOOP authentication work?**  
**Short:** Each athlete completes OAuth once via our **Auth Bridge** (`backend/app.py`). Refresh tokens sit in `whoop_oauth_token`. Nightly `whoop_etl.py` uses those tokens to pull sleep/workout/cycle/recovery.

**Q: Why is WHOOP empty for some athletes?**  
**Short:** They need (1) `whoop_user_id` in the roster, (2) completed OAuth, (3) actual sleep/activity in the lookback window. Missing any step = zero rows — not necessarily a bug.

**Q: How did you fix duplicate WHOOP recovery rows?**  
**Short:** Bronze had multiple ingests per `cycle_id`. Silver uses `ROW_NUMBER()` — keep one row per `(whoop_user_id, cycle_id)`, prefer **SCORED** state, then latest `etl_ingested_at`.

---

### GymAware

**Q: What did “extended GymAware” add?**  
**Short:** Originally only summaries. We added **reps, athletes, bests** export + upload + silver views for richer strength reporting.

**Q: Why chunk `/bests` into 90-day windows?**  
**Short:** Large date ranges timeout or overload the API. `GYMAWARE_BESTS_CHUNK_DAYS` splits the job into smaller requests.

**Q: Why `gymaware_athlete_reference` as BIGINT?**  
**Short:** Some IDs exceeded 32-bit integer max in Postgres — migration to BIGINT prevented overflow errors.

---

### Catapult

**Q: Session-level vs daily rollup?**  
**Short:** Client reviews **each practice session**. `silver_catapult_session` = one row per player per session (periods aggregated). A daily Gold table would hide multiple sessions on the same day.

**Q: What is load index?**  
**Short:** Separate Catapult-derived metric (`load_index.py`) uploaded to `catapult_load_index_*` tables — training load analytics alongside session stats.

---

### Operations

**Q: How does nightly automation work?**  
**Short:** `.github/workflows/daily_etl.yml` runs `scheduled_etl.py --all` with secrets (`DATABASE_URL`, API tokens). Same script works on a laptop with `.env`.

**Q: What happens if one source fails?**  
**Short:** With `--continue-on-error`, other sources still run, but the job **exits non-zero** so we know something failed. JSON summary at end lists failed steps.

**Q: Where are secrets stored?**  
**Short:** `.env` locally (gitignored), GitHub Actions **secrets** in CI. Never committed.

---

### Website / security (honest answers)

**Q: Is the website done?**  
**Short:** **No** — my part is the **data contract** (`web_app_handover.md`). Frontend queries silver views + `athlete_identity`.

**Q: Is the database secure for public internet?**  
**Short:** **RLS not implemented yet** — documented for production. Service role key must stay server-side only.

---

### Tricky “gotcha” questions

| Question | Safe answer |
|----------|-------------|
| “Is it real-time?” | No — scheduled batch, typically daily. |
| “One table for everything?” | No — star pattern: dimension `athlete_identity` + fact silver views. |
| “Did you write the React app?” | No — unless you actually did; point to `frontend/` placeholder. |
| “100% data quality?” | We dedupe in silver; coaches must keep roster IDs accurate. |
| “Catapult 429 errors?” | API rate limits under heavy export — ops tuning, not wrong architecture. |

---

## Part 3 — Code review cheat sheet (explain decisions without deep coding)

**How to use:** Supervisor opens a file → find it below → say **Purpose** + **Why we did it**.

You do **not** need to read every line. Know **what problem** each file solves.

---

### 1. `scheduled_etl.py` — the conductor

**Purpose:** Runs the whole pipeline in order without rewriting export logic.

**Key ideas:**

```42:53:scheduled_etl.py
def run_roster_sync() -> int:
    """Push committed roster workbook into roster_cohort + athlete_identity."""
    rc = _run_step(
        "Roster cohort sync (from workbook)",
        [ROOT / "scripts" / "sync_roster_cohort_from_xlsx.py"],
    )
    ...
    return _run_step(
        "Athlete identity sync (from workbook)",
        [ROOT / "scripts" / "sync_athlete_identity_from_xlsx.py"],
    )
```

| Code pattern | Plain English |
|--------------|---------------|
| `subprocess.run(...)` | Calls existing scripts (export/upload) as separate programs — reuse, don’t duplicate. |
| Roster sync **first** | Database knows athlete IDs before vendor pulls. |
| `continue-on-error` | Finish other sources if Catapult fails; still report failure at end. |
| JSON `summary` at end | Machine-readable log for GitHub Actions debugging. |

**Say:** “I treated ETL as a **pipeline of scripts** orchestrated in one place, with roster sync always first.”

---

### 2. `scripts/sync_athlete_identity_from_xlsx.py` — roster → database

**Purpose:** Coaches edit Excel; this script updates `athlete_identity`.

```30:55:scripts/sync_athlete_identity_from_xlsx.py
UPSERT = """
INSERT INTO public.athlete_identity (...)
ON CONFLICT (internal_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    ...
    whoop_user_id = COALESCE(EXCLUDED.whoop_user_id, athlete_identity.whoop_user_id),
```

| Decision | Why |
|----------|-----|
| **UPSERT** (`ON CONFLICT`) | Running twice doesn’t duplicate rows — updates names/IDs. |
| **COALESCE on IDs** | Empty Excel cell won’t wipe an ID we already had. |
| Reads via `roster_allowlist` | One parser for export filter + DB sync — single source of truth. |

**Say:** “Coaches don’t touch SQL — Excel drives the crosswalk table.”

---

### 3. `integrations/roster_allowlist.py` — read the workbook once

**Purpose:** Load `roster_new.xlsx`, normalize columns (WHOOP ID, GymAware ref, etc.).

| Decision | Why |
|----------|-----|
| Default path `data/roster/roster_new.xlsx` | Works after `git clone` and in CI without extra config. |
| `ROSTER_FILTER` env flag | Turn cohort filtering on/off per environment. |
| Treat `N/A` as empty | Stops bad placeholder strings becoming fake IDs. |

**Say:** “All roster logic goes through one module so export and sync never disagree.”

---

### 4. `schema/silver_whoop.sql` — fix duplicates + add names

**Purpose:** WHOOP bronze grows every night; silver is what the website charts.

**Pattern A — `DISTINCT ON` (cycle, sleep, workout):**

```22:46:schema/silver_whoop.sql
SELECT DISTINCT ON (c.whoop_user_id, c.cycle_id)
    ...
FROM public.whoop_cycle_bi_extract c
LEFT JOIN public.athlete_identity ai
    ON ... ai.whoop_user_id = c.whoop_user_id
ORDER BY c.whoop_user_id, c.cycle_id, c.etl_ingested_at DESC, c.id DESC;
```

| Piece | Meaning |
|-------|---------|
| `DISTINCT ON (...)` | Postgres: keep **one** row per cycle. |
| `ORDER BY ... etl_ingested_at DESC` | That one row = **newest ingest**. |
| `LEFT JOIN athlete_identity` | Adds display name when roster has WHOOP ID. |

**Pattern B — recovery (more complex):**

```159:204:schema/silver_whoop.sql
WITH ranked AS (
    SELECT ..., ROW_NUMBER() OVER (
        PARTITION BY r.whoop_user_id, r.cycle_id
        ORDER BY
            CASE WHEN ... 'SCORED' THEN 0 ELSE 1 END,
            r.etl_ingested_at DESC, ...
    ) AS rn
    ...
)
WHERE x.rn = 1
```

| Piece | Meaning |
|-------|---------|
| `ROW_NUMBER()` | Pick exactly one recovery per cycle. |
| Prefer `SCORED` | WHOOP sometimes has unscored rows — business rule. |
| Join `silver_whoop_cycle` | Attach cycle dates without duplicating rows (earlier bug joined raw cycle and multiplied rows). |

**Say:** “Silver is **SQL views**, not another ETL job — whenever bronze updates, silver automatically reflects latest rules.”

---

### 5. `schema/silver_catapult_session.sql` (same idea, different grain)

**Purpose:** One row per **player per session**; sum period metrics inside that session.

**Say:** “Catapult sends multiple **periods** per activity; silver rolls them up to session level but keeps two sessions on the same day as **two rows** — client requirement.”

---

### 6. `schema/silver_gymaware.sql`

**Purpose:** Dedup summaries, reps, bests; attach athlete names from GymAware reference ID.

**Say:** “GymAware has the richest row count (every rep); silver still dedupes re-ingests like WHOOP.”

---

### 7. `gymaware_export.py` / `upload_gymaware_to_supabase.py`

**Purpose:** Call GymAware REST API → JSON files → Postgres staging + `*_bi_extract`.

**Say:** “Export and upload are separate steps so we can re-upload after a failed DB write without re-calling the API.”

---

### 8. `whoop_etl.py` + `backend/app.py`

| File | Role |
|------|------|
| `backend/app.py` | OAuth login redirect — human step once per athlete. |
| `whoop_etl.py` | Machine step every night — refresh token, pull metrics. |

**Say:** “Split **human auth** from **robot sync** — standard pattern for OAuth APIs.”

---

### 9. `.github/workflows/daily_etl.yml`

**Purpose:** Cloud cron so data refreshes without someone’s laptop.

**Say:** “Secrets in GitHub, roster file in repo, same `scheduled_etl.py` as local — dev/prod parity.”

---

### 10. Files you can name but don’t need line-by-line

| File | One-liner |
|------|-----------|
| `bulk_export.py` / `upload_to_supabase.py` | Catapult pull + load |
| `integrations/gymaware/bi_fields.py` | Flatten JSON; parse `"50.0 kg"` bar weight |
| `medallion_raw_layer_migration.sql` | Added `etl_ingested_at`, ingest IDs |
| `cleanup_legacy_dashboard.sql` | Removed old prototype dashboard tables |
| `verify_integrations.py` | Smoke test APIs before big run |

---

## Part 4 — Live demo script (5–8 minutes)

Do this order if they say “show us”:

1. **GitHub** → `main` → commit `b37efe2` → click `schema/silver_whoop.sql` (30 sec: “dedupe + names”).
2. **GitHub** → `scheduled_etl.py` → scroll `run_roster_sync` (30 sec).
3. **Supabase SQL Editor** — run:

```sql
-- Pick a name you know exists on your roster
SELECT athlete_display_name, calendar_date, recovery_score, resting_heart_rate
FROM public.silver_whoop_recovery
WHERE athlete_display_name IS NOT NULL
ORDER BY calendar_date DESC
LIMIT 10;
```

4. **Compare bronze vs silver (optional wow moment):**

```sql
SELECT COUNT(*) AS bronze_rows FROM public.whoop_recovery_bi_extract;
SELECT COUNT(*) AS silver_rows FROM public.silver_whoop_recovery;
```

Say: “Silver is smaller because duplicates are removed.”

5. **GitHub Actions** (if green): Daily ETL workflow → latest run success.

---

## Part 5 — Your contribution list (customize numbers from journal)

Use this as a template — adjust hours/tasks to match **your** backlog.

| # | Task | Complexity | Proof |
|---|------|------------|-------|
| 1 | Silver layer (WHOOP, Catapult session, GymAware) | High | `schema/silver_*.sql`, commit `b37efe2` |
| 2 | Extended GymAware (reps, athletes, bests) + upload | High | `gymaware_extended.sql`, `gymaware_export.py` |
| 3 | Roster CI + `athlete_identity` sync in scheduler | Medium | `roster_new.xlsx`, `sync_*.py`, `dee7730` |
| 4 | Cross-source + medallion documentation | Medium | `cross_source_correlation.md`, `catapult_medallion_layers.md` |
| 5 | Medallion raw layer / append-only ETL | High | `7d7e7c4`, `medallion_raw_layer_migration.sql` |
| 6 | Legacy dashboard cleanup + handover docs | Medium | `cleanup_legacy_dashboard.sql`, `project_status_handover.md` |
| 7 | Product review documentation pack | Medium | `system_design.md`, `VIVA_PREP.md`, checklist |

**Phrases for individual contribution:**

- “I owned the **analytics data layer**, not the UI.”
- “Medium–high complexity: SQL dedup logic, multi-API ETL, CI integration.”
- “Professional standard: version controlled, documented, repeatable nightly run.”

---

## Part 6 — If you don’t know the answer

| Situation | Say |
|-----------|-----|
| Frontend detail | “I’d defer to [teammate] — my contract is in `web_app_handover.md`.” |
| Deep Python / library | “We used standard libraries — `requests` for APIs, `psycopg2` for Postgres — documented in `requirements.txt`.” |
| Exact line you didn’t write | “That was team baseline; I extended it for silver and GymAware.” |
| Bug you fixed | “We saw duplicate rows in bronze; silver fixes it with latest-ingest wins — documented in `testing_notes.md`.” |

Never guess numbers — say “I can query Supabase to confirm.”

---

## Part 7 — Supporting documentation (20%) — point assessor here

| They ask for… | Open this file |
|---------------|----------------|
| Design / architecture | `docs/design/system_design.md` |
| Handover | `docs/operations/project_status_handover.md` |
| Web team contract | `docs/operations/web_app_handover.md` |
| Tests / debugging | `docs/operations/testing_notes.md` |
| Full rubric map | `docs/operations/product_review_checklist.md` |
| Column definitions | `docs/data_dictionary_baseline.md` |
| How to run | `docs/operations/runbook.md`, `README_HANDOVER.md` |

---

## Part 8 — One-page revision (night before)

1. **Bronze** = raw repeats · **Silver** = clean for UI · **Gold Catapult** = skipped on purpose  
2. **Roster Excel** → `athlete_identity` → names on silver  
3. **scheduled_etl** = roster first, then vendors  
4. **WHOOP** = OAuth once, ETL nightly  
5. **Row counts differ** across sources — normal  
6. **Website** = not my code; **data** = my deliverable  
7. **Demo:** `silver_whoop_recovery` query in Supabase  
8. **Git:** `b37efe2`, silver + docs  

Good luck — you built the hard part (data truth). The viva is explaining **why** those choices were right for the client.
