-- GymAware extended ingest: /reps, /athletes, /bests staging + BI extract tables.
-- Same credentials as summaries (GYMAWARE_ACCOUNT_ID + GYMAWARE_TOKEN). No extra API keys.
--
-- Run after: gymaware_summaries.sql, medallion_raw_layer_migration.sql (etl_ingested_at on summaries).
-- Populated by: gymaware_export.py + upload_gymaware_to_supabase.py (roster filter when ROSTER_FILTER=1).

-- ---------------------------------------------------------------------------
-- Staging (append-only JSONB payloads)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gymaware_reps_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    set_reference TEXT NOT NULL,
    athlete_reference TEXT,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_reps_staging_set_ref
    ON public.gymaware_reps_staging (set_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_reps_staging_athlete
    ON public.gymaware_reps_staging (athlete_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_reps_staging_etl
    ON public.gymaware_reps_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.gymaware_reps_staging IS
    'GymAware GET /reps — one row per set (payload includes reps[] array).';

CREATE TABLE IF NOT EXISTS public.gymaware_athletes_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    athlete_reference TEXT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_athletes_staging_ref
    ON public.gymaware_athletes_staging (athlete_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_athletes_staging_etl
    ON public.gymaware_athletes_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.gymaware_athletes_staging IS
    'GymAware GET /athletes snapshot rows (roster-filtered at export/upload).';

CREATE TABLE IF NOT EXISTS public.gymaware_bests_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    athlete_reference TEXT,
    exercise_name TEXT,
    bar_weight DOUBLE PRECISION,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_bests_staging_athlete
    ON public.gymaware_bests_staging (athlete_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_bests_staging_etl
    ON public.gymaware_bests_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.gymaware_bests_staging IS
    'GymAware GET /bests — personal best per athlete/exercise/bar weight.';

-- ---------------------------------------------------------------------------
-- BI extract (flat columns for dashboards)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gymaware_summaries_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    source_staging_id BIGINT,
    gymaware_reference TEXT NOT NULL,
    recorded DOUBLE PRECISION,
    modified DOUBLE PRECISION,
    athlete_reference TEXT,
    athlete_name TEXT,
    athlete_weight DOUBLE PRECISION,
    exercise_name TEXT,
    exercise_reference TEXT,
    bar_weight DOUBLE PRECISION,
    rep_count INTEGER,
    height DOUBLE PRECISION,
    dip DOUBLE PRECISION,
    mean_velocity DOUBLE PRECISION,
    peak_velocity DOUBLE PRECISION,
    mean_power DOUBLE PRECISION,
    peak_power DOUBLE PRECISION,
    mean_watts_per_kg DOUBLE PRECISION,
    peak_watts_per_kg DOUBLE PRECISION,
    velocity_zone TEXT,
    activity_name TEXT,
    activity_reference TEXT,
    sensor TEXT,
    hardware TEXT,
    notes TEXT,
    deleted BOOLEAN,
    targets_mode TEXT,
    targets_analysis TEXT,
    targets_best_max DOUBLE PRECISION,
    targets_best_min DOUBLE PRECISION,
    targets_last_max DOUBLE PRECISION,
    targets_last_min DOUBLE PRECISION,
    targets_squad_max DOUBLE PRECISION,
    targets_squad_min DOUBLE PRECISION,
    targets_preset_max DOUBLE PRECISION,
    targets_preset_min DOUBLE PRECISION,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_summaries_bi_ref
    ON public.gymaware_summaries_bi_extract (gymaware_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_summaries_bi_athlete
    ON public.gymaware_summaries_bi_extract (athlete_reference);
CREATE INDEX IF NOT EXISTS idx_gymaware_summaries_bi_recorded
    ON public.gymaware_summaries_bi_extract (recorded DESC);

COMMENT ON TABLE public.gymaware_summaries_bi_extract IS
    'Flat /summaries fields from gymaware_summaries (incl. targets.* and metadata).';

CREATE TABLE IF NOT EXISTS public.gymaware_rep_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    source_staging_ingest_id BIGINT,
    set_reference TEXT NOT NULL,
    rep_num INTEGER,
    recorded DOUBLE PRECISION,
    modified DOUBLE PRECISION,
    athlete_reference TEXT,
    athlete_name TEXT,
    athlete_weight DOUBLE PRECISION,
    exercise_name TEXT,
    exercise_reference TEXT,
    bar_weight DOUBLE PRECISION,
    rep_count INTEGER,
    activity_name TEXT,
    activity_reference TEXT,
    rep_metrics JSONB,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_rep_bi_set
    ON public.gymaware_rep_bi_extract (set_reference, rep_num);
CREATE INDEX IF NOT EXISTS idx_gymaware_rep_bi_athlete
    ON public.gymaware_rep_bi_extract (athlete_reference);

COMMENT ON TABLE public.gymaware_rep_bi_extract IS
    'One row per rep from /reps payload; rep_metrics holds per-analysis-type values.';

CREATE TABLE IF NOT EXISTS public.gymaware_athletes_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    source_staging_ingest_id BIGINT NOT NULL,
    athlete_reference TEXT NOT NULL,
    display_name TEXT,
    first_name TEXT,
    last_name TEXT,
    jersey_number TEXT,
    position TEXT,
    sport TEXT,
    address TEXT,
    phone TEXT,
    born TEXT,
    photo TEXT,
    modified DOUBLE PRECISION,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_athletes_bi_ref
    ON public.gymaware_athletes_bi_extract (athlete_reference);

COMMENT ON TABLE public.gymaware_athletes_bi_extract IS
    'Flat GET /athletes profile fields for roster athletes.';

CREATE TABLE IF NOT EXISTS public.gymaware_bests_bi_extract (
    id BIGSERIAL PRIMARY KEY,
    source_staging_ingest_id BIGINT NOT NULL,
    athlete_reference TEXT,
    athlete_name TEXT,
    exercise_name TEXT,
    bar_weight DOUBLE PRECISION,
    height DOUBLE PRECISION,
    dip DOUBLE PRECISION,
    mean_velocity DOUBLE PRECISION,
    peak_velocity DOUBLE PRECISION,
    mean_power DOUBLE PRECISION,
    peak_power DOUBLE PRECISION,
    mean_watts_per_kg DOUBLE PRECISION,
    peak_watts_per_kg DOUBLE PRECISION,
    vendor_synced_at TIMESTAMPTZ,
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gymaware_bests_bi_athlete
    ON public.gymaware_bests_bi_extract (athlete_reference, exercise_name);

COMMENT ON TABLE public.gymaware_bests_bi_extract IS
    'Flat GET /bests personal-best records (per athlete, exercise, bar weight).';
