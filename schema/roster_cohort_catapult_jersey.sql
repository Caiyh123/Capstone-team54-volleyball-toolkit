-- Optional: jersey label for Catapult when athlete UUID is not used (run once in Supabase SQL editor).

ALTER TABLE public.roster_cohort
    ADD COLUMN IF NOT EXISTS catapult_jersey TEXT;

COMMENT ON COLUMN public.roster_cohort.catapult_jersey IS
    'Catapult athlete_jersey from client roster; used by catapult_stats_staging_roster when no UUID.';
