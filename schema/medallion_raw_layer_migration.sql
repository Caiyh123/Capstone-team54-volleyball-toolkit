-- Medallion raw layer: append-only ingestion with etl_ingested_at (no UPSERT into raw staging).
-- Apply ONCE in Supabase SQL Editor after backup. Then deploy updated Python ETL.
--
-- Rationale: preserve every pull for audit/history; deduplicate in Silver/Gold views or Power BI.
-- Operational tables excluded: public.whoop_oauth_token (credential rotation), public.roster_cohort (reference).

-- ---------------------------------------------------------------------------
-- Catapult: catapult_stats_staging — surrogate PK + etl_ingested_at
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'catapult_stats_staging'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'catapult_stats_staging' AND column_name = 'ingest_id'
    ) THEN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'catapult_stats_staging' AND column_name = 'etl_ingested_at'
      ) THEN
        ALTER TABLE public.catapult_stats_staging
          ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
      END IF;
      ALTER TABLE public.catapult_stats_staging ADD COLUMN ingest_id BIGSERIAL;
      ALTER TABLE public.catapult_stats_staging DROP CONSTRAINT catapult_stats_staging_pkey;
      ALTER TABLE public.catapult_stats_staging ADD PRIMARY KEY (ingest_id);
    END IF;
    CREATE INDEX IF NOT EXISTS idx_catapult_stats_staging_activity_etl
      ON public.catapult_stats_staging (activity_id, etl_ingested_at DESC);
  END IF;
END $$;

COMMENT ON COLUMN public.catapult_stats_staging.etl_ingested_at IS 'UTC time this raw row was appended by ETL.';

-- ---------------------------------------------------------------------------
-- GymAware: drop unique on reference (allow duplicate pulls)
-- ---------------------------------------------------------------------------
ALTER TABLE public.gymaware_summaries DROP CONSTRAINT IF EXISTS gymaware_summaries_reference_uq;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'gymaware_summaries' AND column_name = 'etl_ingested_at'
  ) THEN
    ALTER TABLE public.gymaware_summaries
      ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_gymaware_summaries_ref_etl
  ON public.gymaware_summaries (gymaware_reference, etl_ingested_at DESC);

COMMENT ON COLUMN public.gymaware_summaries.etl_ingested_at IS 'UTC time this raw row was appended by ETL.';

-- ---------------------------------------------------------------------------
-- VALD profiles: drop unique (tenant, profile); append-only pulls
-- ---------------------------------------------------------------------------
ALTER TABLE public.vald_profiles DROP CONSTRAINT IF EXISTS vald_profiles_tenant_profile_uq;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'vald_profiles' AND column_name = 'etl_ingested_at'
  ) THEN
    ALTER TABLE public.vald_profiles
      ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_vald_profiles_tenant_profile_etl
  ON public.vald_profiles (tenant_id, profile_id, etl_ingested_at DESC);

COMMENT ON COLUMN public.vald_profiles.etl_ingested_at IS 'UTC time this raw row was appended by ETL.';

-- ---------------------------------------------------------------------------
-- WHOOP staging: surrogate PK + etl_ingested_at (sleep, workout, cycle, recovery)
-- ---------------------------------------------------------------------------

-- Sleep
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'whoop_sleep_staging') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'whoop_sleep_staging' AND column_name = 'ingest_id') THEN
      ALTER TABLE public.whoop_sleep_staging ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
      ALTER TABLE public.whoop_sleep_staging ADD COLUMN ingest_id BIGSERIAL;
      ALTER TABLE public.whoop_sleep_staging DROP CONSTRAINT whoop_sleep_staging_pkey;
      ALTER TABLE public.whoop_sleep_staging ADD PRIMARY KEY (ingest_id);
    END IF;
    CREATE INDEX IF NOT EXISTS idx_whoop_sleep_staging_sleep_id ON public.whoop_sleep_staging (sleep_id);
  END IF;
END $$;

-- Workout
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'whoop_workout_staging') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'whoop_workout_staging' AND column_name = 'ingest_id') THEN
      ALTER TABLE public.whoop_workout_staging ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
      ALTER TABLE public.whoop_workout_staging ADD COLUMN ingest_id BIGSERIAL;
      ALTER TABLE public.whoop_workout_staging DROP CONSTRAINT whoop_workout_staging_pkey;
      ALTER TABLE public.whoop_workout_staging ADD PRIMARY KEY (ingest_id);
    END IF;
    CREATE INDEX IF NOT EXISTS idx_whoop_workout_staging_workout_id ON public.whoop_workout_staging (workout_id);
  END IF;
END $$;

-- Cycle
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'whoop_cycle_staging') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'whoop_cycle_staging' AND column_name = 'ingest_id') THEN
      ALTER TABLE public.whoop_cycle_staging ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
      ALTER TABLE public.whoop_cycle_staging ADD COLUMN ingest_id BIGSERIAL;
      ALTER TABLE public.whoop_cycle_staging DROP CONSTRAINT whoop_cycle_staging_pkey;
      ALTER TABLE public.whoop_cycle_staging ADD PRIMARY KEY (ingest_id);
    END IF;
    CREATE INDEX IF NOT EXISTS idx_whoop_cycle_staging_natural ON public.whoop_cycle_staging (whoop_user_id, cycle_id);
  END IF;
END $$;

-- Recovery
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'whoop_recovery_staging') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'whoop_recovery_staging' AND column_name = 'ingest_id') THEN
      ALTER TABLE public.whoop_recovery_staging ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
      ALTER TABLE public.whoop_recovery_staging ADD COLUMN ingest_id BIGSERIAL;
      ALTER TABLE public.whoop_recovery_staging DROP CONSTRAINT whoop_recovery_staging_pkey;
      ALTER TABLE public.whoop_recovery_staging ADD PRIMARY KEY (ingest_id);
    END IF;
    CREATE INDEX IF NOT EXISTS idx_whoop_recovery_staging_natural ON public.whoop_recovery_staging (whoop_user_id, cycle_id);
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Catapult session metrics (legacy narrow rows): append-only marker
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'catapult_session_metrics' AND column_name = 'etl_ingested_at'
  ) THEN
    ALTER TABLE public.catapult_session_metrics
      ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Load index run: append-only audit of each pipeline run
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'catapult_load_index_run' AND column_name = 'etl_ingested_at'
  ) THEN
    ALTER TABLE public.catapult_load_index_run
      ADD COLUMN etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;
