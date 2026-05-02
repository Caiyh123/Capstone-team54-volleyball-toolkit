# ETL handover (offline / teammate runbook)

Use this when **GitHub Actions** is not available or you need to run the pipeline from a workstation.

## 1. Repository and Python

```bash
git clone <your-repo-url>
cd <repo-root>   # directory that contains requirements.txt and scheduled_etl.py
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Environment file

Copy `.env.example` to `.env` in the **same directory as `scheduled_etl.py`** (the toolkit root). Minimum variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Supabase Postgres connection string (service role or user with INSERT on staging tables) |
| `CATAPULT_TOKEN` | Catapult Connect API bearer token |
| `CATAPULT_BASE_URL` | Optional; default AU API v6 in code. **Do not** create an empty GitHub secret (blank overrides the default). |
| `GYMAWARE_ACCOUNT_ID` | GymAware Cloud Basic auth username |
| `GYMAWARE_TOKEN` | GymAware API token (password) |
| `VALD_CLIENT_ID` / `VALD_CLIENT_SECRET` | VALD OAuth client |
| `VALD_API_BASE_FORCEFRAME` | Optional; ForceFrame host (GET `/tests/v2` summaries) |
| `VALD_API_BASE_FORCEDECKS` | Optional; ForceDecks host (GET `/tests`, trials, definitions) |
| `VALD_FORCEDECKS_TEAM_ID` | Optional UUID; enables detailed tests + **trials** (ForceDecks) |
| `VALD_SKIP_FORCEFRAME_TESTS` | Set `1` to skip ForceFrame upload step only |
| `VALD_SKIP_FORCEDECKS` | Set `1` to skip ForceDecks upload step only |
| `WHOOP_CLIENT_ID` / `WHOOP_CLIENT_SECRET` | WHOOP OAuth app |

Optional scheduling / behavior:

| Variable | Purpose |
|----------|---------|
| `ROSTER_FILTER` | Set `1` to restrict Catapult/GymAware/VALD/WHOOP to the roster workbook |
| `ROSTER_ALLOWLIST_XLSX` | Path to the client roster `.xlsx` if not using the default filename in repo root |
| `SCHEDULED_GYMAWARE_LOOKBACK_DAYS` | Default window for GymAware export |
| `SCHEDULED_WHOOP_LOOKBACK_DAYS` / `WHOOP_ETL_LOOKBACK_DAYS` | WHOOP pull window |
| `SCHEDULED_LOAD_INDEX_LOOKBACK_DAYS` | Load index date window |
| `SCHEDULED_VALD_FORCEFRAME_LOOKBACK_DAYS` / `SCHEDULED_VALD_FORCEDECKS_LOOKBACK_DAYS` | VALD activity pull windows (defaults fall back to 7) |

**Roster workbook:** The repo includes **`data/roster/allowlist.xlsx`** for GitHub Actions (`ROSTER_FILTER=1` + `ROSTER_ALLOWLIST_XLSX` in `.github/workflows/daily_etl.yml`). For local runs with the same file, set `ROSTER_ALLOWLIST_XLSX=data/roster/allowlist.xlsx` in `.env`. Alternatively, keep `Updated Athelete Reference IDs.xlsx` in the toolkit root or parent folder and point `ROSTER_ALLOWLIST_XLSX` at it. Without a resolvable file when filtering is on, ETL exits with an error.

## 3. Supabase DDL (once per project)

In Supabase SQL Editor, run scripts in the order described in `schema/apply_order.txt`, including:

- `schema/medallion_raw_layer_migration.sql` (append-only raw layer: `etl_ingested_at`, surrogate keys)
- Optional VALD activity tables (if using those upload scripts): `vald_forceframe_tests_staging.sql`, `vald_forcedecks_tests_staging.sql`, `vald_forcedecks_trials_staging.sql`, `vald_forcedecks_result_definitions_staging.sql`
- `schema/intermediate_big_table_view.sql` (Power BI intermediate view)

## 4. Daily run (all sources)

From the toolkit root (with `.env` loaded):

```bash
python scheduled_etl.py --all --continue-on-error
```

`--continue-on-error` runs every source even if one fails; the process **exits non-zero** if any step failed (so Task Scheduler / CI reflect real health). The JSON summary at the end of the log lists `failed` sources.

Subset examples:

```bash
python scheduled_etl.py --sources catapult,gymaware
python scheduled_etl.py --all --whoop-dry-run
```

## 5. GitHub Actions (preferred for 24/7)

See `.github/workflows/daily_etl.yml`. Configure **repository secrets** matching the variables above (`DATABASE_URL`, `CATAPULT_TOKEN`, …). If the roster workbook is required in CI, either commit a non-secret copy to the repo (if allowed) or set `ROSTER_FILTER=0` in the workflow `env` for environments without the file.

## 6. Failure triage

- **`etl_ingested_at` / `ingest_id` missing:** Run `schema/medallion_raw_layer_migration.sql`.
- **Supabase Table Editor looks “stale”:** Raw tables are **append-only**; sort or filter by **`etl_ingested_at` DESC** to see the latest load.
- **GitHub Actions green but no new data:** Read the job log JSON summary (`failed` / `steps`); empty optional secrets (e.g. `CATAPULT_BASE_URL`) can break API URLs.
- **WHOOP empty:** Athletes must complete OAuth; check `whoop_oauth_token` and `whoop_etl_run.summary`.
- **VALD profiles only, no activity:** Profiles API is identity only; enable ForceFrame and/or ForceDecks staging DDL + upload scripts. ForceDecks trials need `VALD_FORCEDECKS_TEAM_ID` where applicable. See `docs/volley-etl/vald_volleyball_au_package.md`.
- **Duplicate raw rows:** Expected in append-only mode; dedupe in BI or a downstream view.
