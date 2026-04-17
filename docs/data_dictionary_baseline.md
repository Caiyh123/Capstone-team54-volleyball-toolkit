# Data dictionary (baseline)

This document lists **Supabase tables and columns** that the Python ETL in this repository **writes** or **updates**, plus key **read models** (views). Use it with the client to lock business rules (deduplication, grain, time zones).

**Medallion raw layer:** staging tables below are **append-only** `INSERT` rows with `etl_ingested_at` (and surrogate `ingest_id` where noted). Deduplicate downstream (Silver/Gold views or Power BI), not by UPSERTing raw tables.

**Operational exceptions (UPSERT allowed):** `whoop_oauth_token` (token rotation), `roster_cohort` (reference sync from spreadsheet).

---

## Catapult

### `public.catapult_session_metrics`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | BIGSERIAL | DB default | Surrogate key |
| `activity_id` | UUID | `upload_to_supabase.py` | |
| `athlete_id` | UUID | `upload_to_supabase.py` | Nullable |
| `total_distance` | DOUBLE PRECISION | `upload_to_supabase.py` | |
| `total_player_load` | DOUBLE PRECISION | `upload_to_supabase.py` | |
| `field_time` | DOUBLE PRECISION | `upload_to_supabase.py` | |
| `created_at` | TIMESTAMPTZ | DB default | |
| `etl_ingested_at` | TIMESTAMPTZ | `upload_to_supabase.py` (`NOW()`) | Added by `schema/medallion_raw_layer_migration.sql` |

### `public.catapult_stats_staging`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `ingest_id` | BIGSERIAL | DB default | PK after medallion migration |
| `activity_id` | UUID | `upload_to_supabase.py` | |
| `athlete_id` | UUID | `upload_to_supabase.py` | Nullable |
| `athlete_key` | UUID | GENERATED | Stored generated column |
| `stats_payload` | JSONB | `upload_to_supabase.py` | Full `/stats` row |
| `synced_at` | TIMESTAMPTZ | `upload_to_supabase.py` (`NOW()`) | |
| `etl_ingested_at` | TIMESTAMPTZ | `upload_to_supabase.py` (`NOW()`) | Append-only audit |

### `public.catapult_load_index_run`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | UUID | DB default | PK |
| `start_date` | DATE | `upload_load_index_to_supabase.py` | |
| `end_date` | DATE | `upload_load_index_to_supabase.py` | |
| `sum_player_load` | DOUBLE PRECISION | `upload_load_index_to_supabase.py` | |
| `total_jump_count` | INTEGER | `upload_load_index_to_supabase.py` | |
| `load_index` | DOUBLE PRECISION | `upload_load_index_to_supabase.py` | Nullable |
| `synced_at` | TIMESTAMPTZ | DB default | |
| `etl_ingested_at` | TIMESTAMPTZ | `upload_load_index_to_supabase.py` (`NOW()`) | Added by medallion migration |

### `public.catapult_load_index_activity`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `run_id` | UUID | `upload_load_index_to_supabase.py` | FK → `catapult_load_index_run` |
| `activity_id` | UUID | `upload_load_index_to_supabase.py` | |
| `activity_name` | TEXT | `upload_load_index_to_supabase.py` | |
| `sum_player_load` | DOUBLE PRECISION | `upload_load_index_to_supabase.py` | |
| `jump_count` | INTEGER | `upload_load_index_to_supabase.py` | |
| `load_index_local` | DOUBLE PRECISION | `upload_load_index_to_supabase.py` | Nullable |

---

## GymAware

### `public.gymaware_summaries`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | BIGSERIAL | DB default | |
| `gymaware_reference` | TEXT | `upload_gymaware_to_supabase.py` | Natural key (not unique after migration) |
| `recorded` | DOUBLE PRECISION | `upload_gymaware_to_supabase.py` | Epoch per API (often seconds) |
| `modified` | DOUBLE PRECISION | `upload_gymaware_to_supabase.py` | |
| `athlete_reference` | TEXT | `upload_gymaware_to_supabase.py` | |
| `athlete_name` | TEXT | `upload_gymaware_to_supabase.py` | |
| `athlete_weight` | DOUBLE PRECISION | `upload_gymaware_to_supabase.py` | |
| `exercise_name` | TEXT | `upload_gymaware_to_supabase.py` | |
| `bar_weight` | DOUBLE PRECISION | `upload_gymaware_to_supabase.py` | |
| `rep_count` | INTEGER | `upload_gymaware_to_supabase.py` | |
| `targets` | JSONB | `upload_gymaware_to_supabase.py` | |
| `height` … `activity_reference` | Various | `upload_gymaware_to_supabase.py` | See `schema/gymaware_summaries.sql` |
| `raw` | JSONB | `upload_gymaware_to_supabase.py` | Full export row |
| `created_at` | TIMESTAMPTZ | DB default | |
| `updated_at` | TIMESTAMPTZ | `upload_gymaware_to_supabase.py` (`NOW()`) | |
| `etl_ingested_at` | TIMESTAMPTZ | `upload_gymaware_to_supabase.py` (`NOW()`) | Append-only audit |

---

## VALD

### `public.vald_profiles`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | BIGSERIAL | DB default | |
| `tenant_id` | TEXT | `upload_vald_profiles_to_supabase.py` | |
| `profile_id` | TEXT | `upload_vald_profiles_to_supabase.py` | |
| `sync_id` | TEXT | `upload_vald_profiles_to_supabase.py` | |
| `given_name` … `being_merged_with_expiry_utc` | Various | `upload_vald_profiles_to_supabase.py` | See `schema/vald_profiles.sql` |
| `raw` | JSONB | `upload_vald_profiles_to_supabase.py` | |
| `created_at` | TIMESTAMPTZ | DB default | |
| `updated_at` | TIMESTAMPTZ | `upload_vald_profiles_to_supabase.py` (`NOW()`) | |
| `etl_ingested_at` | TIMESTAMPTZ | `upload_vald_profiles_to_supabase.py` (`NOW()`) | Append-only audit |

---

## WHOOP

### `public.whoop_oauth_token` (operational UPSERT)

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | UUID | DB / bridge | |
| `state_label` | TEXT | OAuth bridge | Often GymAware roster key |
| `whoop_user_id` | TEXT | OAuth bridge / ETL | Unique |
| `refresh_token` | TEXT | OAuth bridge | Secret |
| `access_token` | TEXT | `integrations/whoop/token_store.py` | Rotated |
| `expires_at` | TIMESTAMPTZ | token store | |
| `scope` | TEXT | OAuth | |
| `raw_token_response` | JSONB | OAuth | |
| `created_at` / `updated_at` | TIMESTAMPTZ | DB / UPSERT | |
| `needs_reconnect` | BOOLEAN | bridge / ETL | |

### `public.whoop_sleep_staging`, `whoop_workout_staging`, `whoop_cycle_staging`, `whoop_recovery_staging`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `ingest_id` | BIGSERIAL | DB default | PK after migration |
| Natural key columns (`sleep_id`, `workout_id`, …) | UUID/BIGINT/TEXT | `integrations/whoop/etl.py` | Indexed, not PK after migration |
| `whoop_user_id` | TEXT | `integrations/whoop/etl.py` | |
| `payload` | JSONB | `integrations/whoop/etl.py` | API response |
| `synced_at` | TIMESTAMPTZ | `integrations/whoop/etl.py` (`NOW()`) | |
| `etl_ingested_at` | TIMESTAMPTZ | `integrations/whoop/etl.py` (`NOW()`) | Append-only audit |

### `public.whoop_etl_run`

| Column | Type | Written by | Notes |
|--------|------|------------|--------|
| `id` | BIGSERIAL | DB default | |
| `finished_at` | TIMESTAMPTZ | DB default | |
| `lookback_days` | INTEGER | `whoop_etl.py` | |
| `window_start` / `window_end` | TEXT | `whoop_etl.py` | |
| `ok` | BOOLEAN | `whoop_etl.py` | |
| `summary` | JSONB | `whoop_etl.py` | |

---

## Roster / identity (reference)

### `public.roster_cohort`

Maintained by `scripts/sync_roster_cohort_from_xlsx.py` (UPSERT on `gymaware_athlete_reference`). Columns: `gymaware_athlete_reference`, `vald_profile_id`, `display_label`, `catapult_jersey`, `updated_at`.

### `public.athlete_identity`

Populated manually or by your process; not filled by the scheduled vendor ETL scripts in this repo. See `schema/athlete_identity.sql`.

---

## Views (read models)

| View | Purpose |
|------|---------|
| `public.catapult_stats_staging_flat` | Scalar fields from Catapult JSONB + `ingest_id` / `etl_ingested_at` |
| `public.intermediate_big_table` | Catapult `catapult_stats_staging` row + identity/roster + VALD + GymAware (JSON) + WHOOP sleep (no dependency on `catapult_stats_staging_flat`) |
| `public.*_roster` | Cohort-scoped vendor views (`schema/roster_filtered_views.sql`) |

---

## Apply order (DDL)

See `schema/apply_order.txt`. Run **`schema/medallion_raw_layer_migration.sql`** after base staging DDL and before relying on append-only Python ETL.
