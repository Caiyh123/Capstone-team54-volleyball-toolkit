-- WHOOP ETL staging (JSONB payloads from GET /developer/v2/...).
-- Apply after schema/whoop_oauth_tokens.sql. Schedule: python whoop_etl.py

CREATE TABLE IF NOT EXISTS public.whoop_sleep_staging (
    sleep_id UUID NOT NULL,
    whoop_user_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sleep_id)
);

CREATE INDEX IF NOT EXISTS idx_whoop_sleep_staging_user
    ON public.whoop_sleep_staging (whoop_user_id);

CREATE TABLE IF NOT EXISTS public.whoop_workout_staging (
    workout_id UUID NOT NULL,
    whoop_user_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workout_id)
);

CREATE INDEX IF NOT EXISTS idx_whoop_workout_staging_user
    ON public.whoop_workout_staging (whoop_user_id);

CREATE TABLE IF NOT EXISTS public.whoop_cycle_staging (
    whoop_user_id TEXT NOT NULL,
    cycle_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (whoop_user_id, cycle_id)
);

CREATE TABLE IF NOT EXISTS public.whoop_recovery_staging (
    whoop_user_id TEXT NOT NULL,
    cycle_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (whoop_user_id, cycle_id)
);

CREATE TABLE IF NOT EXISTS public.whoop_etl_run (
    id BIGSERIAL PRIMARY KEY,
    finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lookback_days INTEGER,
    window_start TEXT,
    window_end TEXT,
    ok BOOLEAN NOT NULL DEFAULT TRUE,
    summary JSONB
);

COMMENT ON TABLE public.whoop_sleep_staging IS 'WHOOP v2 sleep activities; join payload->user_id or whoop_user_id.';
COMMENT ON TABLE public.whoop_etl_run IS 'Optional audit row per whoop_etl.py run.';
