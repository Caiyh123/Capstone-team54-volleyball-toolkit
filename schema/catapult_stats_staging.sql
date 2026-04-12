-- Full Catapult POST /stats row per (activity, athlete) for BI (JSONB).
-- Run after catapult_session_metrics.sql. Load: python upload_to_supabase.py (after bulk_export.py).

CREATE TABLE IF NOT EXISTS public.catapult_stats_staging (
    activity_id UUID NOT NULL,
    athlete_id UUID,
    -- Stable join key when athlete_id is null (single unknown athlete per activity)
    athlete_key UUID GENERATED ALWAYS AS (
        COALESCE(
            athlete_id,
            '00000000-0000-0000-0000-000000000000'::uuid
        )
    ) STORED,
    stats_payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (activity_id, athlete_key)
);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_staging_synced_at
    ON public.catapult_stats_staging (synced_at DESC);

CREATE INDEX IF NOT EXISTS idx_catapult_stats_staging_payload_gin
    ON public.catapult_stats_staging USING gin (stats_payload);

COMMENT ON TABLE public.catapult_stats_staging IS
    'Full OpenField /stats row per athlete per activity from bulk_export.json; BI source of truth beyond catapult_session_metrics.';
