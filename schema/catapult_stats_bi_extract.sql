-- BI-friendly scalar extract from Catapult POST /stats (stats_payload).
-- Physical table (not a view). Append rows after each staging ingest for history, or
-- truncate + reload if you prefer a snapshot table.
-- Populated automatically by upload_to_supabase.py (one row per new catapult_stats_staging.ingest_id).
--
-- Prerequisites: public.catapult_stats_staging with ingest_id (run medallion_raw_layer_migration.sql first).
-- Apply in Supabase SQL Editor after catapult_stats_staging.sql (+ medallion migration).

CREATE TABLE IF NOT EXISTS public.catapult_stats_bi_extract (
    id BIGSERIAL PRIMARY KEY,

    -- Grain + lineage
    activity_id UUID NOT NULL,
    athlete_id UUID,
    athlete_key UUID NOT NULL,
    source_staging_ingest_id BIGINT,
    participating_athlete_id UUID,
    source_activity_id UUID,

    -- Context (from stats_payload)
    athlete_jersey TEXT,
    team_name TEXT,
    activity_name TEXT,
    period_name TEXT,
    stats_date TEXT,
    date_id TEXT,
    date_name TEXT,

    -- Time (seconds unless noted)
    start_time DOUBLE PRECISION,
    end_time DOUBLE PRECISION,
    field_time DOUBLE PRECISION,
    bench_time DOUBLE PRECISION,
    duration DOUBLE PRECISION,

    -- Velocity / HR
    max_vel DOUBLE PRECISION,
    athlete_max_velocity DOUBLE PRECISION,
    percentage_max_velocity DOUBLE PRECISION,
    max_heart_rate DOUBLE PRECISION,
    min_heart_rate DOUBLE PRECISION,
    athlete_max_hr DOUBLE PRECISION,
    percentage_max_heart_rate DOUBLE PRECISION,
    percentage_avg_heart_rate DOUBLE PRECISION,

    -- Player load
    total_player_load DOUBLE PRECISION,
    player_load_per_minute DOUBLE PRECISION,
    peak_player_load DOUBLE PRECISION,
    total_2d_player_load DOUBLE PRECISION,

    -- Jump totals / rates (Catapult key names use slashes → safe column names here)
    total_jumps DOUBLE PRECISION,
    indoor_analytics_total_jump_count DOUBLE PRECISION,
    jumps_per_minute DOUBLE PRECISION,
    high_jump_per_minute DOUBLE PRECISION,
    high_jumps_p_per_minute DOUBLE PRECISION,

    -- IMA jump counts by intensity band (OpenField band thresholds apply)
    ima_band1_jump_count DOUBLE PRECISION,
    ima_band2_jump_count DOUBLE PRECISION,
    ima_band3_jump_count DOUBLE PRECISION,
    ima_band4_jump_count DOUBLE PRECISION,
    ima_band5_jump_count DOUBLE PRECISION,
    ima_band6_jump_count DOUBLE PRECISION,
    ima_band7_jump_count DOUBLE PRECISION,
    ima_band8_jump_count DOUBLE PRECISION,

    -- ETL / sync audit
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_bi_extract_activity
    ON public.catapult_stats_bi_extract (activity_id);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_bi_extract_athlete_key
    ON public.catapult_stats_bi_extract (athlete_key);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_bi_extract_etl
    ON public.catapult_stats_bi_extract (etl_ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_bi_extract_source_ingest
    ON public.catapult_stats_bi_extract (source_staging_ingest_id DESC);

COMMENT ON TABLE public.catapult_stats_bi_extract IS
    'Scalar Catapult /stats fields extracted from catapult_stats_staging.stats_payload for BI; one row per staging ingest row copied.';

COMMENT ON COLUMN public.catapult_stats_bi_extract.source_staging_ingest_id IS
    'ingest_id from catapult_stats_staging row this extract was built from (lineage).';

COMMENT ON COLUMN public.catapult_stats_bi_extract.vendor_synced_at IS
    'synced_at from staging when the extract was produced (Catapult pull time on staging row).';

COMMENT ON COLUMN public.catapult_stats_bi_extract.etl_ingested_at IS
    'UTC time this extract row was inserted into this table.';

COMMENT ON COLUMN public.catapult_stats_bi_extract.high_jump_per_minute IS
    'Maps stats_payload key high_jump/min.';

COMMENT ON COLUMN public.catapult_stats_bi_extract.high_jumps_p_per_minute IS
    'Maps stats_payload key high_jumps_p/min.';

COMMENT ON COLUMN public.catapult_stats_bi_extract.jumps_per_minute IS
    'Maps stats_payload key jumps/minute.';

-- ---------------------------------------------------------------------------
-- Example: populate from latest staging rows (run after each upload or on schedule)
-- ---------------------------------------------------------------------------
-- INSERT INTO public.catapult_stats_bi_extract (
--     activity_id, athlete_id, athlete_key, source_staging_ingest_id,
--     participating_athlete_id, source_activity_id,
--     athlete_jersey, team_name, activity_name, period_name, stats_date, date_id, date_name,
--     start_time, end_time, field_time, bench_time, duration,
--     max_vel, athlete_max_velocity, percentage_max_velocity,
--     max_heart_rate, min_heart_rate, athlete_max_hr, percentage_max_heart_rate, percentage_avg_heart_rate,
--     total_player_load, player_load_per_minute, peak_player_load, total_2d_player_load,
--     total_jumps, indoor_analytics_total_jump_count, jumps_per_minute, high_jump_per_minute, high_jumps_p_per_minute,
--     ima_band1_jump_count, ima_band2_jump_count, ima_band3_jump_count, ima_band4_jump_count,
--     ima_band5_jump_count, ima_band6_jump_count, ima_band7_jump_count, ima_band8_jump_count,
--     vendor_synced_at, etl_ingested_at
-- )
-- SELECT
--     s.activity_id,
--     s.athlete_id,
--     s.athlete_key,
--     s.ingest_id,
--     (s.stats_payload->'participating_athlete'->>'id')::uuid,
--     (s.stats_payload->>'source_activity_id')::uuid,
--     s.stats_payload->>'athlete_jersey',
--     s.stats_payload->>'team_name',
--     s.stats_payload->>'activity_name',
--     s.stats_payload->>'period_name',
--     s.stats_payload->>'date',
--     s.stats_payload->>'date_id',
--     s.stats_payload->>'date_name',
--     (s.stats_payload->>'start_time')::double precision,
--     (s.stats_payload->>'end_time')::double precision,
--     (s.stats_payload->>'field_time')::double precision,
--     (s.stats_payload->>'bench_time')::double precision,
--     (s.stats_payload->>'duration')::double precision,
--     (s.stats_payload->>'max_vel')::double precision,
--     (s.stats_payload->>'athlete_max_velocity')::double precision,
--     (s.stats_payload->>'percentage_max_velocity')::double precision,
--     (s.stats_payload->>'max_heart_rate')::double precision,
--     (s.stats_payload->>'min_heart_rate')::double precision,
--     (s.stats_payload->>'athlete_max_hr')::double precision,
--     (s.stats_payload->>'percentage_max_heart_rate')::double precision,
--     (s.stats_payload->>'percentage_avg_heart_rate')::double precision,
--     (s.stats_payload->>'total_player_load')::double precision,
--     (s.stats_payload->>'player_load_per_minute')::double precision,
--     (s.stats_payload->>'peak_player_load')::double precision,
--     (s.stats_payload->>'total_2d_player_load')::double precision,
--     (s.stats_payload->>'total_jumps')::double precision,
--     (s.stats_payload->>'indoor_analytics_total_jump_count')::double precision,
--     (s.stats_payload->>'jumps/minute')::double precision,
--     (s.stats_payload->>'high_jump/min')::double precision,
--     (s.stats_payload->>'high_jumps_p/min')::double precision,
--     (s.stats_payload->>'ima_band1_jump_count')::double precision,
--     (s.stats_payload->>'ima_band2_jump_count')::double precision,
--     (s.stats_payload->>'ima_band3_jump_count')::double precision,
--     (s.stats_payload->>'ima_band4_jump_count')::double precision,
--     (s.stats_payload->>'ima_band5_jump_count')::double precision,
--     (s.stats_payload->>'ima_band6_jump_count')::double precision,
--     (s.stats_payload->>'ima_band7_jump_count')::double precision,
--     (s.stats_payload->>'ima_band8_jump_count')::double precision,
--     s.synced_at,
--     NOW()
-- FROM public.catapult_stats_staging s
-- WHERE s.ingest_id IN (
--     SELECT MAX(ingest_id) FROM public.catapult_stats_staging GROUP BY activity_id, athlete_key
-- );
