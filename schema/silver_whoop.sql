-- Silver WHOOP views: dedupe append-only bronze BI rows; attach athlete names from athlete_identity.
--
-- Bronze *_bi_extract tables grow on every ETL run (triggers on staging). Silver keeps
-- one row per natural key (cycle_id, sleep_id, workout_id) and adds:
--   athlete_internal_key, athlete_display_name, calendar_date (UTC)
--
-- Apply after: whoop_bi_extract.sql, athlete_identity.sql (populate via roster sync).
-- Power BI: use silver_* views, not raw whoop_*_bi_extract.

-- ---------------------------------------------------------------------------
-- Cycle (physiological day container)
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS public.silver_whoop_sleep_longest_per_day CASCADE;
DROP VIEW IF EXISTS public.silver_whoop_recovery CASCADE;
DROP VIEW IF EXISTS public.silver_whoop_workout CASCADE;
DROP VIEW IF EXISTS public.silver_whoop_sleep CASCADE;
DROP VIEW IF EXISTS public.silver_whoop_cycle CASCADE;

CREATE VIEW public.silver_whoop_cycle
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (c.whoop_user_id, c.cycle_id)
    c.whoop_user_id,
    c.cycle_id,
    c.member_user_id,
    c.score_state,
    c.start_ts,
    c.end_ts,
    c.created_at,
    c.updated_at,
    c.timezone_offset,
    c.strain,
    c.kilojoule,
    c.average_heart_rate,
    c.max_heart_rate,
    c.source_staging_ingest_id,
    c.etl_ingested_at,
    c.id AS latest_bi_extract_id,
    (c.start_ts AT TIME ZONE 'UTC')::date AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    ai.display_name AS athlete_display_name
FROM public.whoop_cycle_bi_extract c
LEFT JOIN public.athlete_identity ai
    ON btrim(ai.whoop_user_id) <> ''
   AND ai.whoop_user_id = c.whoop_user_id
ORDER BY c.whoop_user_id, c.cycle_id, c.etl_ingested_at DESC, c.id DESC;

COMMENT ON VIEW public.silver_whoop_cycle IS
    'One row per WHOOP cycle; deduped ETL ingests. Strain window for the physiological day.';

-- ---------------------------------------------------------------------------
-- Sleep (one row per sleep_id — main sleep and naps stay separate rows)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_whoop_sleep
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (s.sleep_id)
    s.sleep_id,
    s.whoop_user_id,
    s.cycle_id,
    s.member_user_id,
    s.nap,
    s.score_state,
    s.start_ts,
    s.end_ts,
    s.created_at,
    s.updated_at,
    s.timezone_offset,
    s.respiratory_rate,
    s.sleep_performance_percentage,
    s.sleep_consistency_percentage,
    s.sleep_efficiency_percentage,
    s.total_in_bed_time_milli,
    s.total_awake_time_milli,
    s.total_no_data_time_milli,
    s.total_light_sleep_time_milli,
    s.total_slow_wave_sleep_time_milli,
    s.total_rem_sleep_time_milli,
    s.sleep_cycle_count,
    s.disturbance_count,
    s.sleep_needed_baseline_milli,
    s.sleep_needed_from_sleep_debt_milli,
    s.sleep_needed_from_recent_strain_milli,
    s.sleep_needed_from_recent_nap_milli,
    s.source_staging_ingest_id,
    s.etl_ingested_at,
    s.id AS latest_bi_extract_id,
    COALESCE(
        (s.end_ts AT TIME ZONE 'UTC')::date,
        (s.start_ts AT TIME ZONE 'UTC')::date
    ) AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    ai.display_name AS athlete_display_name
FROM public.whoop_sleep_bi_extract s
LEFT JOIN public.athlete_identity ai
    ON btrim(ai.whoop_user_id) <> ''
   AND ai.whoop_user_id = s.whoop_user_id
ORDER BY s.sleep_id, s.etl_ingested_at DESC, s.id DESC;

COMMENT ON VIEW public.silver_whoop_sleep IS
    'One row per WHOOP sleep_id (deduped). calendar_date = wake day (end_ts UTC) unless missing.';

-- ---------------------------------------------------------------------------
-- Workout (one row per workout_id — multiple workouts per day are valid)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_whoop_workout
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (w.workout_id)
    w.workout_id,
    w.whoop_user_id,
    w.member_user_id,
    w.sport_id,
    w.sport_name,
    w.score_state,
    w.start_ts,
    w.end_ts,
    w.created_at,
    w.updated_at,
    w.timezone_offset,
    w.strain,
    w.average_heart_rate,
    w.max_heart_rate,
    w.kilojoule,
    w.percent_recorded,
    w.distance_meter,
    w.altitude_gain_meter,
    w.altitude_change_meter,
    w.zone_zero_milli,
    w.zone_one_milli,
    w.zone_two_milli,
    w.zone_three_milli,
    w.zone_four_milli,
    w.zone_five_milli,
    w.source_staging_ingest_id,
    w.etl_ingested_at,
    w.id AS latest_bi_extract_id,
    COALESCE(
        (w.start_ts AT TIME ZONE 'UTC')::date,
        (w.created_at AT TIME ZONE 'UTC')::date
    ) AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    ai.display_name AS athlete_display_name
FROM public.whoop_workout_bi_extract w
LEFT JOIN public.athlete_identity ai
    ON btrim(ai.whoop_user_id) <> ''
   AND ai.whoop_user_id = w.whoop_user_id
ORDER BY w.workout_id, w.etl_ingested_at DESC, w.id DESC;

COMMENT ON VIEW public.silver_whoop_workout IS
    'One row per WHOOP workout_id (deduped). Multiple workouts per athlete per day are expected.';

-- ---------------------------------------------------------------------------
-- Recovery (one row per cycle — summary HRV / RHR)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_whoop_recovery
WITH (security_invoker = true)
AS
WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.whoop_user_id, r.cycle_id
            ORDER BY
                CASE WHEN upper(coalesce(r.score_state, '')) = 'SCORED' THEN 0 ELSE 1 END,
                r.etl_ingested_at DESC,
                r.id DESC
        ) AS rn
    FROM public.whoop_recovery_bi_extract r
)
SELECT
    x.whoop_user_id,
    x.cycle_id,
    x.sleep_id,
    x.score_state,
    x.recovery_score,
    x.resting_heart_rate,
    x.hrv_rmssd_milli,
    x.spo2_percentage,
    x.skin_temp_celsius,
    x.user_calibrating,
    x.created_at,
    x.updated_at,
    x.source_staging_ingest_id,
    x.etl_ingested_at,
    x.id AS latest_bi_extract_id,
    c.start_ts AS cycle_start_ts,
    c.end_ts AS cycle_end_ts,
    c.strain AS cycle_strain,
    c.kilojoule AS cycle_kilojoule,
    COALESCE(
        (c.start_ts AT TIME ZONE 'UTC')::date,
        (x.created_at AT TIME ZONE 'UTC')::date
    ) AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    ai.display_name AS athlete_display_name
FROM ranked x
LEFT JOIN public.silver_whoop_cycle c
    ON c.whoop_user_id = x.whoop_user_id
   AND c.cycle_id = x.cycle_id
LEFT JOIN public.athlete_identity ai
    ON btrim(ai.whoop_user_id) <> ''
   AND ai.whoop_user_id = x.whoop_user_id
WHERE x.rn = 1;

COMMENT ON VIEW public.silver_whoop_recovery IS
    'One recovery per WHOOP cycle; prefers SCORED. Use for summary HRV/RHR with athlete names.';

-- ---------------------------------------------------------------------------
-- Longest sleep per athlete per calendar day (optional summary / future use)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_whoop_sleep_longest_per_day
WITH (security_invoker = true)
AS
WITH ranked AS (
    SELECT
        s.*,
        ROW_NUMBER() OVER (
            PARTITION BY
                s.whoop_user_id,
                s.calendar_date
            ORDER BY
                COALESCE(s.total_in_bed_time_milli, 0) DESC,
                CASE WHEN COALESCE(s.nap, false) THEN 1 ELSE 0 END,
                s.etl_ingested_at DESC
        ) AS rn
    FROM public.silver_whoop_sleep s
    WHERE s.calendar_date IS NOT NULL
)
SELECT
    whoop_user_id,
    calendar_date,
    athlete_internal_key,
    athlete_display_name,
    sleep_id,
    nap,
    score_state,
    start_ts,
    end_ts,
    total_in_bed_time_milli,
    sleep_performance_percentage,
    sleep_efficiency_percentage,
    total_rem_sleep_time_milli,
    total_slow_wave_sleep_time_milli,
    total_light_sleep_time_milli,
    etl_ingested_at
FROM ranked
WHERE rn = 1;

COMMENT ON VIEW public.silver_whoop_sleep_longest_per_day IS
    'Longest in-bed sleep per athlete per calendar_date (wake day). For optional summary KPIs; naps excluded when a longer main sleep exists.';
