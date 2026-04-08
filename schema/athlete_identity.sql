-- Crosswalk table: stable internal athlete key + vendor-specific IDs (nullable).
-- Run in Supabase SQL editor after review. Adjust column names to match your roster process.

CREATE TABLE IF NOT EXISTS public.athlete_identity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internal_key TEXT NOT NULL,
    display_name TEXT,
    catapult_athlete_id TEXT,
    gymaware_athlete_reference INTEGER,
    vald_profile_id TEXT,
    whoop_user_id TEXT,
    teamworks_athlete_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT athlete_identity_internal_key_unique UNIQUE (internal_key)
);

CREATE INDEX IF NOT EXISTS idx_athlete_identity_gymaware
    ON public.athlete_identity (gymaware_athlete_reference)
    WHERE gymaware_athlete_reference IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_athlete_identity_catapult
    ON public.athlete_identity (catapult_athlete_id)
    WHERE catapult_athlete_id IS NOT NULL;

COMMENT ON TABLE public.athlete_identity IS
    'Maps roster/internal IDs to Catapult, GymAware, VALD, WHOOP, Teamworks. Populate from client spreadsheet.';
