-- Run in Supabase: Dashboard → SQL → New query → Run
-- GymAware GET /summaries — one row per set (gymaware_bulk_export.json shape).
-- Upsert imports on gymaware_reference.

CREATE TABLE IF NOT EXISTS public.gymaware_summaries (
    id BIGSERIAL PRIMARY KEY,
    gymaware_reference TEXT NOT NULL,
    recorded DOUBLE PRECISION,
    modified DOUBLE PRECISION,
    athlete_reference TEXT,
    athlete_name TEXT,
    athlete_weight DOUBLE PRECISION,
    exercise_name TEXT,
    bar_weight DOUBLE PRECISION,
    rep_count INTEGER,
    targets JSONB,
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
    raw JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT gymaware_summaries_reference_uq UNIQUE (gymaware_reference)
);

CREATE INDEX IF NOT EXISTS gymaware_summaries_athlete_ref_idx
    ON public.gymaware_summaries (athlete_reference);

CREATE INDEX IF NOT EXISTS gymaware_summaries_recorded_idx
    ON public.gymaware_summaries (recorded);

CREATE INDEX IF NOT EXISTS gymaware_summaries_activity_ref_idx
    ON public.gymaware_summaries (activity_reference);

COMMENT ON TABLE public.gymaware_summaries IS 'GymAware Cloud /summaries; recorded/modified = API epoch seconds (float).';
