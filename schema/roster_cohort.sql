-- Confirmed athlete cohort for analytics (Power BI, SQL clients).
-- Populate with: python scripts/sync_roster_cohort_from_xlsx.py
-- Or INSERT from your process; then use *_roster views for read access.

CREATE TABLE IF NOT EXISTS public.roster_cohort (
    gymaware_athlete_reference BIGINT PRIMARY KEY,
    vald_profile_id TEXT,
    display_label TEXT,
    catapult_jersey TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roster_cohort_vald_profile
    ON public.roster_cohort (vald_profile_id)
    WHERE vald_profile_id IS NOT NULL;

COMMENT ON TABLE public.roster_cohort IS
    'Client-approved roster keys; join GymAware reference to limit rows in BI views.';
