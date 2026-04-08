-- Run in Supabase: Dashboard → SQL → New query → Run
-- Then: python upload_to_supabase.py

CREATE TABLE IF NOT EXISTS public.catapult_session_metrics (
    id BIGSERIAL PRIMARY KEY,
    activity_id UUID NOT NULL,
    athlete_id UUID,
    total_distance DOUBLE PRECISION,
    total_player_load DOUBLE PRECISION,
    field_time DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS catapult_session_metrics_activity_id_idx
    ON public.catapult_session_metrics (activity_id);

COMMENT ON TABLE public.catapult_session_metrics IS 'Catapult Connect stats uploaded from bulk_export.json';
