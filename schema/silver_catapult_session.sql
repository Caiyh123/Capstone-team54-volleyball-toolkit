-- Silver Catapult: one row per player per session (activity_id + athlete_key).
--
-- Layering:
--   Bronze: catapult_stats_bi_extract (append-only; duplicate ingests possible)
--   Silver: silver_catapult_session (this view)
--   Gold:   optional gold_catapult_athlete_day (NOT implemented — client uses session-level
--           stats; see docs/volley-etl/catapult_medallion_layers.md)
--
-- Logic:
--   1) Latest row per (activity_id, athlete_key, period_name) — removes random duplicate ETL ingests.
--   2) SUM additive metrics across periods within the same session; MAX for peak/rate fields.
--
-- Prerequisites: catapult_stats_bi_extract.sql, medallion_raw_layer_migration.sql,
--                  athlete_identity.sql + roster_cohort.sql (optional; for athlete_internal_key).
-- Power BI: use this view for Catapult detail pages, not raw catapult_stats_bi_extract.

DROP VIEW IF EXISTS public.silver_catapult_session CASCADE;

CREATE VIEW public.silver_catapult_session
WITH (security_invoker = true)
AS
WITH latest_period_row AS (
    SELECT DISTINCT ON (
        b.activity_id,
        b.athlete_key,
        COALESCE(b.period_name, '')
    )
        b.*
    FROM public.catapult_stats_bi_extract b
    ORDER BY
        b.activity_id,
        b.athlete_key,
        COALESCE(b.period_name, ''),
        b.etl_ingested_at DESC,
        b.id DESC
),
session_agg AS (
    SELECT
        p.activity_id,
        p.athlete_key,

        (ARRAY_AGG(p.athlete_id ORDER BY p.etl_ingested_at DESC)
            FILTER (WHERE p.athlete_id IS NOT NULL))[1] AS athlete_id,
        (ARRAY_AGG(p.participating_athlete_id ORDER BY p.etl_ingested_at DESC)
            FILTER (WHERE p.participating_athlete_id IS NOT NULL))[1] AS participating_athlete_id,
        (ARRAY_AGG(p.source_activity_id ORDER BY p.etl_ingested_at DESC)
            FILTER (WHERE p.source_activity_id IS NOT NULL))[1] AS source_activity_id,
        MAX(p.athlete_jersey) AS athlete_jersey,
        MAX(p.team_name) AS team_name,
        MAX(p.activity_name) AS activity_name,
        MAX(p.stats_date) AS stats_date,
        MAX(p.date_id) AS date_id,
        MAX(p.date_name) AS date_name,

        MIN(p.start_time) AS start_time,
        MAX(p.end_time) AS end_time,
        SUM(p.field_time) AS field_time,
        SUM(p.bench_time) AS bench_time,
        SUM(p.duration) AS duration,

        MAX(p.max_vel) AS max_vel,
        MAX(p.athlete_max_velocity) AS athlete_max_velocity,
        MAX(p.percentage_max_velocity) AS percentage_max_velocity,
        MAX(p.max_heart_rate) AS max_heart_rate,
        MIN(p.min_heart_rate) AS min_heart_rate,
        MAX(p.athlete_max_hr) AS athlete_max_hr,
        MAX(p.percentage_max_heart_rate) AS percentage_max_heart_rate,
        MAX(p.percentage_avg_heart_rate) AS percentage_avg_heart_rate,

        SUM(p.total_player_load) AS total_player_load,
        MAX(p.player_load_per_minute) AS player_load_per_minute,
        MAX(p.peak_player_load) AS peak_player_load,
        SUM(p.total_2d_player_load) AS total_2d_player_load,

        SUM(p.total_jumps) AS total_jumps,
        SUM(p.indoor_analytics_total_jump_count) AS indoor_analytics_total_jump_count,
        MAX(p.jumps_per_minute) AS jumps_per_minute,
        MAX(p.high_jump_per_minute) AS high_jump_per_minute,
        MAX(p.high_jumps_p_per_minute) AS high_jumps_p_per_minute,

        SUM(p.ima_band1_jump_count) AS ima_band1_jump_count,
        SUM(p.ima_band2_jump_count) AS ima_band2_jump_count,
        SUM(p.ima_band3_jump_count) AS ima_band3_jump_count,
        SUM(p.ima_band4_jump_count) AS ima_band4_jump_count,
        SUM(p.ima_band5_jump_count) AS ima_band5_jump_count,
        SUM(p.ima_band6_jump_count) AS ima_band6_jump_count,
        SUM(p.ima_band7_jump_count) AS ima_band7_jump_count,
        SUM(p.ima_band8_jump_count) AS ima_band8_jump_count,

        (SUM(COALESCE(p.ima_band6_jump_count, 0))
         + SUM(COALESCE(p.ima_band7_jump_count, 0))
         + SUM(COALESCE(p.ima_band8_jump_count, 0))) AS high_jump_count_ima_bands_6_8,

        COUNT(*)::integer AS period_count,
        STRING_AGG(DISTINCT NULLIF(btrim(p.period_name), ''), ', ' ORDER BY NULLIF(btrim(p.period_name), ''))
            AS period_names,

        MAX(p.vendor_synced_at) AS vendor_synced_at,
        MAX(p.etl_ingested_at) AS etl_ingested_at,
        MAX(p.source_staging_ingest_id) AS source_staging_ingest_id,
        MAX(p.id) AS latest_bi_extract_id
    FROM latest_period_row p
    GROUP BY p.activity_id, p.athlete_key
)
SELECT
    s.activity_id,
    s.athlete_key,
    s.athlete_id,
    s.participating_athlete_id,
    s.source_activity_id,
    s.athlete_jersey,
    s.team_name,
    s.activity_name,
    s.stats_date,
    s.date_id,
    s.date_name,
    s.start_time,
    s.end_time,
    s.field_time,
    s.bench_time,
    s.duration,
    s.max_vel,
    s.athlete_max_velocity,
    s.percentage_max_velocity,
    s.max_heart_rate,
    s.min_heart_rate,
    s.athlete_max_hr,
    s.percentage_max_heart_rate,
    s.percentage_avg_heart_rate,
    s.total_player_load,
    s.player_load_per_minute,
    s.peak_player_load,
    s.total_2d_player_load,
    s.total_jumps,
    s.indoor_analytics_total_jump_count,
    s.jumps_per_minute,
    s.high_jump_per_minute,
    s.high_jumps_p_per_minute,
    s.ima_band1_jump_count,
    s.ima_band2_jump_count,
    s.ima_band3_jump_count,
    s.ima_band4_jump_count,
    s.ima_band5_jump_count,
    s.ima_band6_jump_count,
    s.ima_band7_jump_count,
    s.ima_band8_jump_count,
    s.high_jump_count_ima_bands_6_8,
    s.period_count,
    s.period_names,
    s.vendor_synced_at,
    s.etl_ingested_at,
    s.source_staging_ingest_id,
    s.latest_bi_extract_id,

    COALESCE(
        CASE
            WHEN btrim(s.stats_date) <> '' AND btrim(s.stats_date) ~ '^\d{4}-\d{2}-\d{2}$' THEN
                btrim(s.stats_date)::date
            ELSE NULL
        END,
        CASE
            WHEN s.start_time IS NOT NULL AND s.start_time > 0 THEN
                (to_timestamp(s.start_time) AT TIME ZONE 'UTC')::date
            ELSE NULL
        END
    ) AS calendar_date,

    COALESCE(ai_uuid.internal_key, ai_jersey.internal_key) AS athlete_internal_key,
    COALESCE(ai_uuid.display_name, ai_jersey.display_name) AS athlete_display_name
FROM session_agg s
LEFT JOIN public.athlete_identity ai_uuid
    ON s.athlete_id IS NOT NULL
   AND btrim(ai_uuid.catapult_athlete_id) <> ''
   AND lower(btrim(ai_uuid.catapult_athlete_id)) = lower(s.athlete_id::text)
LEFT JOIN public.roster_cohort rc
    ON ai_uuid.internal_key IS NULL
   AND s.athlete_jersey IS NOT NULL
   AND btrim(s.athlete_jersey) <> ''
   AND btrim(rc.catapult_jersey) <> ''
   AND lower(btrim(rc.catapult_jersey)) = lower(btrim(s.athlete_jersey))
LEFT JOIN public.athlete_identity ai_jersey
    ON ai_uuid.internal_key IS NULL
   AND rc.gymaware_athlete_reference IS NOT NULL
   AND ai_jersey.gymaware_athlete_reference = rc.gymaware_athlete_reference;

COMMENT ON VIEW public.silver_catapult_session IS
    'One row per Catapult session (activity_id + athlete_key): deduped ETL ingests, periods summed within session.';

COMMENT ON COLUMN public.silver_catapult_session.period_count IS
    'Number of distinct periods (after dedupe) rolled into this session row.';

COMMENT ON COLUMN public.silver_catapult_session.high_jump_count_ima_bands_6_8 IS
    'Sum of IMA bands 6–8 jump counts across periods; tenant-specific high-intensity proxy.';

COMMENT ON COLUMN public.silver_catapult_session.calendar_date IS
    'Session date from stats_date or UTC start_time; adjust timezone in Gold layer if needed.';
