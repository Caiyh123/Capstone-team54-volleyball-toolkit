-- WHOOP scalar BI extracts: flat columns from JSONB payloads for dashboards (Power BI, etc.).
-- Populated automatically via AFTER INSERT triggers on whoop_*_staging.
--
-- Run AFTER:
--   - schema/whoop_staging.sql
--   - schema/medallion_raw_layer_migration.sql (staging tables must have ingest_id + PK on ingest_id)
--
-- Paste into Supabase SQL Editor (or add to migration pipeline).

-- ---------------------------------------------------------------------------
-- Sleep
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.whoop_sleep_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    sleep_id UUID NOT NULL,
    whoop_user_id TEXT NOT NULL,
    source_staging_ingest_id BIGINT NOT NULL,
    member_user_id BIGINT,
    cycle_id BIGINT,
    nap BOOLEAN,
    score_state TEXT,
    start_ts TIMESTAMPTZ,
    end_ts TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    timezone_offset TEXT,
    respiratory_rate DOUBLE PRECISION,
    sleep_performance_percentage DOUBLE PRECISION,
    sleep_consistency_percentage DOUBLE PRECISION,
    sleep_efficiency_percentage DOUBLE PRECISION,
    total_in_bed_time_milli BIGINT,
    total_awake_time_milli BIGINT,
    total_no_data_time_milli BIGINT,
    total_light_sleep_time_milli BIGINT,
    total_slow_wave_sleep_time_milli BIGINT,
    total_rem_sleep_time_milli BIGINT,
    sleep_cycle_count INTEGER,
    disturbance_count INTEGER,
    sleep_needed_baseline_milli BIGINT,
    sleep_needed_from_sleep_debt_milli BIGINT,
    sleep_needed_from_recent_strain_milli BIGINT,
    sleep_needed_from_recent_nap_milli BIGINT,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whoop_sleep_bi_extract_sleep
    ON public.whoop_sleep_bi_extract (sleep_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_bi_extract_user
    ON public.whoop_sleep_bi_extract (whoop_user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_bi_extract_start
    ON public.whoop_sleep_bi_extract (start_ts DESC);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_bi_extract_source
    ON public.whoop_sleep_bi_extract (source_staging_ingest_id DESC);

COMMENT ON TABLE public.whoop_sleep_bi_extract IS
    'WHOOP sleep /v2/activity/sleep flattened from whoop_sleep_staging.payload; one row per staging insert.';

CREATE OR REPLACE FUNCTION public.tf_whoop_sleep_staging_bi_extract()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.whoop_sleep_bi_extract (
        sleep_id, whoop_user_id, source_staging_ingest_id,
        member_user_id, cycle_id, nap, score_state,
        start_ts, end_ts, created_at, updated_at, timezone_offset,
        respiratory_rate, sleep_performance_percentage, sleep_consistency_percentage, sleep_efficiency_percentage,
        total_in_bed_time_milli, total_awake_time_milli, total_no_data_time_milli,
        total_light_sleep_time_milli, total_slow_wave_sleep_time_milli, total_rem_sleep_time_milli,
        sleep_cycle_count, disturbance_count,
        sleep_needed_baseline_milli, sleep_needed_from_sleep_debt_milli,
        sleep_needed_from_recent_strain_milli, sleep_needed_from_recent_nap_milli,
        vendor_synced_at, etl_ingested_at
    )
    VALUES (
        NEW.sleep_id,
        NEW.whoop_user_id,
        NEW.ingest_id,
        (NULLIF(NEW.payload->>'user_id', ''))::bigint,
        (NULLIF(NEW.payload->>'cycle_id', ''))::bigint,
        (NEW.payload->>'nap')::boolean,
        NEW.payload->>'score_state',
        (NULLIF(NEW.payload->>'start', ''))::timestamptz,
        (NULLIF(NEW.payload->>'end', ''))::timestamptz,
        (NULLIF(NEW.payload->>'created_at', ''))::timestamptz,
        (NULLIF(NEW.payload->>'updated_at', ''))::timestamptz,
        NEW.payload->>'timezone_offset',
        (NULLIF(NEW.payload #>> '{score,respiratory_rate}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,sleep_performance_percentage}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,sleep_consistency_percentage}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,sleep_efficiency_percentage}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_in_bed_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_awake_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_no_data_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_light_sleep_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_slow_wave_sleep_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,total_rem_sleep_time_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,stage_summary,sleep_cycle_count}', ''))::integer,
        (NULLIF(NEW.payload #>> '{score,stage_summary,disturbance_count}', ''))::integer,
        (NULLIF(NEW.payload #>> '{score,sleep_needed,baseline_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,sleep_needed,need_from_sleep_debt_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,sleep_needed,need_from_recent_strain_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,sleep_needed,need_from_recent_nap_milli}', ''))::bigint,
        NEW.synced_at,
        COALESCE(NEW.etl_ingested_at, NOW())
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_whoop_sleep_staging_bi_extract ON public.whoop_sleep_staging;
CREATE TRIGGER tr_whoop_sleep_staging_bi_extract
    AFTER INSERT ON public.whoop_sleep_staging
    FOR EACH ROW
    EXECUTE FUNCTION public.tf_whoop_sleep_staging_bi_extract();

-- ---------------------------------------------------------------------------
-- Workout
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.whoop_workout_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    workout_id UUID NOT NULL,
    whoop_user_id TEXT NOT NULL,
    source_staging_ingest_id BIGINT NOT NULL,
    member_user_id BIGINT,
    sport_id INTEGER,
    sport_name TEXT,
    score_state TEXT,
    start_ts TIMESTAMPTZ,
    end_ts TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    timezone_offset TEXT,
    strain DOUBLE PRECISION,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    kilojoule DOUBLE PRECISION,
    percent_recorded DOUBLE PRECISION,
    distance_meter DOUBLE PRECISION,
    altitude_gain_meter DOUBLE PRECISION,
    altitude_change_meter DOUBLE PRECISION,
    zone_zero_milli BIGINT,
    zone_one_milli BIGINT,
    zone_two_milli BIGINT,
    zone_three_milli BIGINT,
    zone_four_milli BIGINT,
    zone_five_milli BIGINT,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whoop_workout_bi_extract_workout
    ON public.whoop_workout_bi_extract (workout_id);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_bi_extract_user
    ON public.whoop_workout_bi_extract (whoop_user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_bi_extract_start
    ON public.whoop_workout_bi_extract (start_ts DESC);

COMMENT ON TABLE public.whoop_workout_bi_extract IS
    'WHOOP workout /v2/activity/workout flattened from whoop_workout_staging.payload.';

CREATE OR REPLACE FUNCTION public.tf_whoop_workout_staging_bi_extract()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.whoop_workout_bi_extract (
        workout_id, whoop_user_id, source_staging_ingest_id,
        member_user_id, sport_id, sport_name, score_state,
        start_ts, end_ts, created_at, updated_at, timezone_offset,
        strain, average_heart_rate, max_heart_rate, kilojoule, percent_recorded,
        distance_meter, altitude_gain_meter, altitude_change_meter,
        zone_zero_milli, zone_one_milli, zone_two_milli, zone_three_milli, zone_four_milli, zone_five_milli,
        vendor_synced_at, etl_ingested_at
    )
    VALUES (
        NEW.workout_id,
        NEW.whoop_user_id,
        NEW.ingest_id,
        (NULLIF(NEW.payload->>'user_id', ''))::bigint,
        (NULLIF(NEW.payload->>'sport_id', ''))::integer,
        NEW.payload->>'sport_name',
        NEW.payload->>'score_state',
        (NULLIF(NEW.payload->>'start', ''))::timestamptz,
        (NULLIF(NEW.payload->>'end', ''))::timestamptz,
        (NULLIF(NEW.payload->>'created_at', ''))::timestamptz,
        (NULLIF(NEW.payload->>'updated_at', ''))::timestamptz,
        NEW.payload->>'timezone_offset',
        (NULLIF(NEW.payload #>> '{score,strain}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,average_heart_rate}', ''))::integer,
        (NULLIF(NEW.payload #>> '{score,max_heart_rate}', ''))::integer,
        (NULLIF(NEW.payload #>> '{score,kilojoule}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,percent_recorded}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,distance_meter}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,altitude_gain_meter}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,altitude_change_meter}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_zero_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_one_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_two_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_three_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_four_milli}', ''))::bigint,
        (NULLIF(NEW.payload #>> '{score,zone_durations,zone_five_milli}', ''))::bigint,
        NEW.synced_at,
        COALESCE(NEW.etl_ingested_at, NOW())
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_whoop_workout_staging_bi_extract ON public.whoop_workout_staging;
CREATE TRIGGER tr_whoop_workout_staging_bi_extract
    AFTER INSERT ON public.whoop_workout_staging
    FOR EACH ROW
    EXECUTE FUNCTION public.tf_whoop_workout_staging_bi_extract();

-- ---------------------------------------------------------------------------
-- Recovery
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.whoop_recovery_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    whoop_user_id TEXT NOT NULL,
    cycle_id BIGINT NOT NULL,
    source_staging_ingest_id BIGINT NOT NULL,
    sleep_id UUID,
    member_user_id BIGINT,
    score_state TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    user_calibrating BOOLEAN,
    recovery_score DOUBLE PRECISION,
    resting_heart_rate DOUBLE PRECISION,
    hrv_rmssd_milli DOUBLE PRECISION,
    spo2_percentage DOUBLE PRECISION,
    skin_temp_celsius DOUBLE PRECISION,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whoop_recovery_bi_extract_cycle
    ON public.whoop_recovery_bi_extract (whoop_user_id, cycle_id);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_bi_extract_sleep
    ON public.whoop_recovery_bi_extract (sleep_id);

COMMENT ON TABLE public.whoop_recovery_bi_extract IS
    'WHOOP recovery /v2/recovery flattened from whoop_recovery_staging.payload.';

CREATE OR REPLACE FUNCTION public.tf_whoop_recovery_staging_bi_extract()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.whoop_recovery_bi_extract (
        whoop_user_id, cycle_id, source_staging_ingest_id,
        sleep_id, member_user_id, score_state, created_at, updated_at,
        user_calibrating, recovery_score, resting_heart_rate, hrv_rmssd_milli,
        spo2_percentage, skin_temp_celsius,
        vendor_synced_at, etl_ingested_at
    )
    VALUES (
        NEW.whoop_user_id,
        NEW.cycle_id,
        NEW.ingest_id,
        (NULLIF(NEW.payload->>'sleep_id', ''))::uuid,
        (NULLIF(NEW.payload->>'user_id', ''))::bigint,
        NEW.payload->>'score_state',
        (NULLIF(NEW.payload->>'created_at', ''))::timestamptz,
        (NULLIF(NEW.payload->>'updated_at', ''))::timestamptz,
        (NEW.payload->'score'->>'user_calibrating')::boolean,
        (NULLIF(NEW.payload #>> '{score,recovery_score}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,resting_heart_rate}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,hrv_rmssd_milli}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,spo2_percentage}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,skin_temp_celsius}', ''))::double precision,
        NEW.synced_at,
        COALESCE(NEW.etl_ingested_at, NOW())
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_whoop_recovery_staging_bi_extract ON public.whoop_recovery_staging;
CREATE TRIGGER tr_whoop_recovery_staging_bi_extract
    AFTER INSERT ON public.whoop_recovery_staging
    FOR EACH ROW
    EXECUTE FUNCTION public.tf_whoop_recovery_staging_bi_extract();

-- ---------------------------------------------------------------------------
-- Cycle (physiological day / strain container)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.whoop_cycle_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    whoop_user_id TEXT NOT NULL,
    cycle_id BIGINT NOT NULL,
    source_staging_ingest_id BIGINT NOT NULL,
    member_user_id BIGINT,
    score_state TEXT,
    start_ts TIMESTAMPTZ,
    end_ts TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    timezone_offset TEXT,
    strain DOUBLE PRECISION,
    kilojoule DOUBLE PRECISION,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whoop_cycle_bi_extract_natural
    ON public.whoop_cycle_bi_extract (whoop_user_id, cycle_id);
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_bi_extract_start
    ON public.whoop_cycle_bi_extract (start_ts DESC);

COMMENT ON TABLE public.whoop_cycle_bi_extract IS
    'WHOOP cycle /v2/cycle flattened from whoop_cycle_staging.payload.';

CREATE OR REPLACE FUNCTION public.tf_whoop_cycle_staging_bi_extract()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.whoop_cycle_bi_extract (
        whoop_user_id, cycle_id, source_staging_ingest_id,
        member_user_id, score_state, start_ts, end_ts, created_at, updated_at, timezone_offset,
        strain, kilojoule, average_heart_rate, max_heart_rate,
        vendor_synced_at, etl_ingested_at
    )
    VALUES (
        NEW.whoop_user_id,
        NEW.cycle_id,
        NEW.ingest_id,
        (NULLIF(NEW.payload->>'user_id', ''))::bigint,
        NEW.payload->>'score_state',
        (NULLIF(NEW.payload->>'start', ''))::timestamptz,
        (NULLIF(NEW.payload->>'end', ''))::timestamptz,
        (NULLIF(NEW.payload->>'created_at', ''))::timestamptz,
        (NULLIF(NEW.payload->>'updated_at', ''))::timestamptz,
        NEW.payload->>'timezone_offset',
        (NULLIF(NEW.payload #>> '{score,strain}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,kilojoule}', ''))::double precision,
        (NULLIF(NEW.payload #>> '{score,average_heart_rate}', ''))::integer,
        (NULLIF(NEW.payload #>> '{score,max_heart_rate}', ''))::integer,
        NEW.synced_at,
        COALESCE(NEW.etl_ingested_at, NOW())
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_whoop_cycle_staging_bi_extract ON public.whoop_cycle_staging;
CREATE TRIGGER tr_whoop_cycle_staging_bi_extract
    AFTER INSERT ON public.whoop_cycle_staging
    FOR EACH ROW
    EXECUTE FUNCTION public.tf_whoop_cycle_staging_bi_extract();

-- Backfill: triggers only fire on new inserts. Existing staging rows can be copied with
-- INSERT ... SELECT mirroring the trigger expressions, WHERE NOT EXISTS (... source_staging_ingest_id),
-- or re-run whoop_etl.py for the same UTC window (append-only staging will gain new ingest_id rows).
