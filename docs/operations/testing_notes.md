# Testing and verification notes

Evidence for product reliability: smoke tests, ETL checks, and known issues.

## Automated / repeatable checks

| Test | Command | Expected |
|------|---------|----------|
| Env configured | `python scripts/preflight_config.py` | Required vars reported yes/no (no secrets printed) |
| API connectivity | `python verify_integrations.py` | Catapult/GymAware (and VALD if configured) respond |
| Python syntax | GitHub Actions `ci.yml` | `python -m compileall` passes |
| Full pipeline | `python scheduled_etl.py --all` | JSON summary; exit 0 if all steps OK |

## Manual ETL verification (after a run)

1. **Latest ingest:** In Supabase, sort bronze tables by `etl_ingested_at DESC` — confirm new timestamp.
2. **WHOOP audit:** `SELECT * FROM whoop_etl_run ORDER BY started_at DESC LIMIT 5;`
3. **Silver dedup:** Compare counts bronze vs silver, e.g.:

```sql
SELECT COUNT(*) FROM catapult_stats_bi_extract;
SELECT COUNT(*) FROM silver_catapult_session;
```

Silver count should be ≤ bronze (deduped).

4. **Names on silver:**

```sql
SELECT COUNT(*) FILTER (WHERE athlete_display_name IS NOT NULL)
FROM silver_whoop_recovery;
```

Should match roster-linked WHOOP users.

## Test cases (representative)

| ID | Scenario | Steps | Pass criteria |
|----|----------|-------|---------------|
| T1 | Roster sync | Run `sync_athlete_identity_from_xlsx.py` | `athlete_identity` rows match workbook |
| T2 | Roster-filtered Catapult | `ROSTER_FILTER=1`, run Catapult upload | Only cohort athletes in staging |
| T3 | GymAware extended | Run `gymaware_export.py` + upload | Rows in `gymaware_*_bi_extract` |
| T4 | WHOOP ETL | Token present, run `whoop_etl.py` | New rows in `whoop_*_staging` / bi_extract |
| T5 | Silver apply | Run `silver_whoop.sql` in SQL Editor | Views exist; queries return data |
| T6 | Cross-source filter | Query two silver views same athlete/date | Different row counts OK; same `athlete_display_name` |

## Debugging notes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Duplicate KPIs in reports | Querying `*_bi_extract` not silver | Switch to `silver_*` views |
| WHOOP empty | No OAuth / no data in lookback | OAuth flow; increase lookback days |
| GymAware bests timeout | Large date range | Default 90-day chunks (`GYMAWARE_BESTS_CHUNK_DAYS`) |
| Catapult 429 | API rate limit on bulk export | Reduce concurrency; retry later |
| `gymaware_athlete_reference` overflow | Old INTEGER column | Apply `athlete_identity_gymaware_bigint.sql` |
| Inflated Catapult SUM in BI | Summing bronze with duplicate ingests | Use `silver_catapult_session` |

## Results (project snapshot)

- Scheduled ETL `--all` completed successfully in team environment with production credentials.
- Silver views validated on dev Supabase after applying `silver_catapult_session.sql`, `silver_whoop.sql`, `silver_gymaware.sql`.
- Legacy dashboard tables removed without breaking ETL.

Frontend UI testing is owned by the website sub-team (out of scope for this document).
