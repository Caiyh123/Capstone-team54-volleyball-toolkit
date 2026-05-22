# Cross-source correlation (final sprint)

## The problem

Catapult, WHOOP, and GymAware will **never** have the same number of rows per athlete per day:

| Source | Typical rows per day |
|--------|----------------------|
| WHOOP | 1 recovery per **cycle** (+ separate sleep/workout rows) |
| Catapult | 0–n **sessions** |
| GymAware | Many **sets/reps** |

That is expected. Correlation uses **athlete + calendar date + correct silver grain**, not matching row counts.

## Duplicate ingests (WHOOP)

If this returns many rows:

```sql
SELECT whoop_user_id, cycle_id, COUNT(*)
FROM public.whoop_recovery_bi_extract
GROUP BY 1, 2 HAVING COUNT(*) > 1;
```

those are **ETL re-ingests of the same cycle** (counts of 3–6), not multiple recoveries. Use **`silver_whoop_recovery`** (one row per `whoop_user_id` + `cycle_id`).

## Silver objects for reporting

| View | Grain | Use for |
|------|--------|---------|
| `silver_catapult_session` | Player × session | Catapult detail; session table on summary |
| `silver_whoop_recovery` | Player × WHOOP cycle | Summary HRV, RHR, recovery % |
| `silver_whoop_sleep` | Player × sleep_id | WHOOP sleep detail |
| `silver_whoop_workout` | Player × workout_id | WHOOP workouts |
| `silver_whoop_cycle` | Player × cycle | Cycle strain / dates |
| `silver_whoop_sleep_longest_per_day` | Player × day | Optional main sleep KPI |

All WHOOP silver views include **`athlete_display_name`** and **`athlete_internal_key`** when `athlete_identity.whoop_user_id` is set (from `roster_new.xlsx` sync).

### GymAware silver (`schema/silver_gymaware.sql`)

| View | Use for |
|------|---------|
| `silver_gymaware_summaries` | Sets / summary metrics |
| `silver_gymaware_rep` | Rep-level detail |
| `silver_gymaware_bests` | Personal bests |
| `silver_gymaware_athletes` | Athlete profiles |

### Catapult silver

`silver_catapult_session` — already includes `athlete_internal_key`, `athlete_display_name`.

### Power BI slicer

Use **`athlete_display_name`** on any silver table, or a single **`athlete_identity`** dimension related on `internal_key` / vendor IDs.

Bronze `*_bi_extract` tables remain for audit only.

## Power BI: one filter for the whole page

1. **`athlete_identity`** → `dim_athlete` (`internal_key`, `display_name`)
2. **`dim_date`** (calendar table)
3. Relationships:
   - `silver_whoop_recovery[athlete_internal_key]` → `dim_athlete[internal_key]`
   - `silver_whoop_recovery[calendar_date]` → `dim_date[Date]`
   - `silver_catapult_session` → same keys
   - GymAware facts → `gymaware_athlete_reference` or identity
4. **Sync slicers** on athlete and date — do not put separate WHOOP/Catapult name filters on each chart.

## Summary page measures (examples)

| Card | Table | Measure |
|------|--------|---------|
| HRV | `silver_whoop_recovery` | `MAX(hrv_rmssd_milli)` with `score_state = SCORED` |
| RHR | `silver_whoop_recovery` | `MAX(resting_heart_rate)` |
| Sessions / load | `silver_catapult_session` | Table of sessions, or `SUM(total_player_load)` if daily total needed |

WHOOP **workouts** and **sleep** stay on the WHOOP detail page (`whoop_workout_bi_extract`, `whoop_sleep_bi_extract`) — do not merge into the recovery row.

## What we are not doing

- One wide table joining every workout × session × rep
- Catapult Gold (daily rollup) — client wants session-level Catapult
- Forcing equal row counts across sources
