# Web application handover (data contract)

The custom website should read **silver views** and **`athlete_identity`** from Supabase. The ETL team does not own the React/UI layer; this document defines the database contract.

## Authentication (TBD by frontend)

- Option A: Supabase client with **RLS** policies per role (not yet implemented).
- Option B: Backend API using **service role** `DATABASE_URL` (server-side only; never expose in browser).

## Athlete picker (global filter)

Use **`public.athlete_identity`**:

| Column | Use |
|--------|-----|
| `internal_key` | Stable join key across pages |
| `display_name` | UI label (or map from roster) |
| `whoop_user_id`, `gymaware_athlete_reference`, etc. | Vendor-specific drill-downs |

Filter all fact queries by **`athlete_internal_key`** or **`athlete_display_name`** on silver views (both populated when roster sync has vendor IDs).

## Summary page (one athlete + one date)

| Source | View | Grain |
|--------|------|--------|
| WHOOP recovery KPIs | `silver_whoop_recovery` | One row per WHOOP cycle |
| Catapult session list | `silver_catapult_session` | One row per player × session |
| Optional main sleep | `silver_whoop_sleep_longest_per_day` | One row per player × day |

Row counts **will differ** across sources on the same calendar day — expected. See `docs/volley-etl/cross_source_correlation.md`.

## Detail pages

| Tab | Silver view |
|-----|-------------|
| Catapult | `silver_catapult_session` |
| WHOOP sleep | `silver_whoop_sleep` |
| WHOOP workout | `silver_whoop_workout` |
| WHOOP recovery | `silver_whoop_recovery` |
| WHOOP cycle | `silver_whoop_cycle` |
| GymAware summaries | `silver_gymaware_summaries` |
| GymAware reps | `silver_gymaware_rep` |
| GymAware bests | `silver_gymaware_bests` |

## Do not use for UI metrics

- Raw `*_bi_extract` tables (duplicate ingests).
- Dropped legacy objects: `dashboard_design`, `vw_dashboard_*`, `intermediate_big_table`.

## Schema apply order

If standing up a new Supabase project: `schema/apply_order.txt` (bronze → BI extract → silver).

## Sample filter (SQL)

```sql
SELECT *
FROM public.silver_whoop_recovery
WHERE athlete_display_name = 'Jane Example'
  AND calendar_date = '2026-05-20';
```

Equivalent in app code: filter `athlete_internal_key` + `calendar_date` on each silver query.
