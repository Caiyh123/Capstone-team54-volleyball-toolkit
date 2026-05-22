# Product review checklist (Capstone Team 54 — data platform)

Maps the **Product Review** rubric to this repository. Use during viva prep: each team member should own rows in **Individual contribution** and be able to demo **Technical understanding** items for their work.

**Legend:** ✅ Done · ⚠️ Partial / shared / frontend-owned · ❌ Not done (optional or other team)

---

## Assessment criteria (must score ≥50% in each)

| Criterion | Weight | Data/ETL status |
|-----------|--------|-----------------|
| Individual Contribution | 40% | Per-person — fill in journal/backlog |
| Technical Understanding | 40% | Prep from `system_design.md` + your modules |
| Product Quality & Client Alignment | 40% | Data platform ✅; full product ⚠️ (website behind) |
| Supporting Documentation | 20% | ✅ Improved in this commit |

---

## 1. Individual Contribution (40%)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Substantial tasks (medium–high complexity) | **Per member** | Backlog/journal + git history |
| Aligned with project objectives | ✅ Team | Unified athlete analytics pipeline |
| Professional quality (structure, functionality) | ✅ Data lane | `scheduled_etl.py`, integrations, schema, CI |
| Git commits show owned work | **Per member** | `git log --author` |

**Your prep:** List 3–5 tasks you personally built (e.g. WHOOP ETL, silver SQL, GymAware extended, roster sync, GitHub Actions).

---

## 2. Technical Understanding (40%)

| Topic | Status | Where to demo |
|-------|--------|---------------|
| Explain ETL pipeline end-to-end | ✅ | `scheduled_etl.py`, `docs/design/system_design.md` |
| Bronze vs silver vs gold | ✅ | `catapult_medallion_layers.md`, silver SQL |
| Why append-only + dedup views | ✅ | `cross_source_correlation.md` |
| Roster / `athlete_identity` | ✅ | `roster_new.xlsx`, sync scripts |
| WHOOP OAuth + refresh | ✅ | `backend/app.py`, `whoop_etl.py` |
| Design decisions justified | ✅ | `system_design.md` §5 |
| Testing / verification | ✅ | `testing_notes.md`, `verify_integrations.py` |
| Frontend architecture | ⚠️ Other member | `frontend/`, `web_app_handover.md` |

**Viva questions to rehearse:** Why not one wide table? Why is Catapult Gold deferred? Why do WHOOP and Catapult row counts differ on the same day?

---

## 3. Product Quality & Client Alignment (40%)

| Client requirement | Status | Notes |
|--------------------|--------|-------|
| Multi-source data in one database | ✅ | Supabase |
| Scheduled automated refresh | ✅ | `daily_etl.yml`, Task Scheduler |
| Coach-editable roster | ✅ | `roster_new.xlsx` + sync |
| Catapult session-level analytics | ✅ | `silver_catapult_session` |
| GymAware training data | ✅ | Extended export + silver |
| WHOOP recovery/sleep/workout | ✅ | ETL + silver (needs per-athlete OAuth) |
| VALD profiles / optional tests | ✅ | Upload scripts in pipeline |
| Custom website (replacing Power BI) | ⚠️ | Data contract ready; UI in progress |
| Unified athlete filter (name + date) | ✅ | Silver + `athlete_identity` |
| Privacy / cohort scope | ✅ | `ROSTER_FILTER=1` |
| Production security (RLS) | ❌ Optional | Documented; not implemented |

**Honest framing for review:** Data platform meets client analytics needs; presentation layer is the remaining gap, not the pipeline.

---

## 4. Supporting Documentation (20%)

| Requirement | Status | Location |
|-------------|--------|----------|
| Version control (Git) | ✅ | GitHub repo; daily ETL workflow |
| Design document (workflow, decisions) | ✅ | `docs/design/system_design.md` |
| Operations / handover | ✅ | `project_status_handover.md`, `README_HANDOVER.md`, `runbook.md` |
| Data dictionary | ✅ | `docs/data_dictionary_baseline.md` |
| Cross-source / correlation guide | ✅ | `cross_source_correlation.md` |
| Web consumer contract | ✅ | `web_app_handover.md` |
| Test cases / debugging | ✅ | `testing_notes.md` |
| Code comments on significant logic | ⚠️ | Key modules commented; not every file |
| External references / attribution | ⚠️ | Vendor docs cited in design doc; expand in report if needed |
| Track changes on Word docs | **N/A** | Code-centric project |

---

## 5. Review day checklist (logistics)

| Item | Status |
|------|--------|
| Book supervisor time slot | **Team** |
| Zoom link ready | **Team** |
| Screen share GitHub + Supabase + (optional) Actions log | ✅ Prep |
| Show `scheduled_etl.py` run or green Action | ✅ Prep |
| Show silver query in Supabase SQL Editor | ✅ Prep |
| Backlog/journal matches claimed work | **Per member** |
| Each member speaks to own contribution | **Required** |

---

## 6. CLO mapping (course learning outcomes)

| CLO | How this project addresses it |
|-----|-------------------------------|
| CLO1 Domain + PM | Medallion ETL, CI, roster process, runbook |
| CLO2 Team contribution | Split: data platform vs frontend vs client liaison |
| CLO3 Justify deliverables | Client session-level Catapult; silver for web; deferred Gold |
| CLO4 Reflection | Individual viva — prepare lessons (OAuth, dedup, rate limits) |
| CLO5 Ethics/culture | Roster allowlist, PII in WHOOP, RLS noted for production |
| CLO6 Handover documentation | This checklist + handover + design + web contract |

---

## Summary: is everything complete?

| Area | Complete? |
|------|-----------|
| **Data / ETL / Supabase silver (your scope)** | ✅ Yes for capstone data deliverable |
| **Full end-user product (website)** | ⚠️ In progress — not a fail of data work if contract is documented |
| **Documentation for rubric** | ✅ Yes after this update + git push |
| **Optional (RLS, all athletes on WHOOP, Gold)** | ❌ Post-review / optional |

**Action before viva:** Each member updates personal contribution list; confirm Supabase has all `silver_*.sql` applied; show one green `daily_etl` run.
