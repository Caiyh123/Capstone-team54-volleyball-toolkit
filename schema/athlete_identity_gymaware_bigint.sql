-- GymAware API IDs exceed INTEGER max (~2.1e9). Run once if athlete_identity sync fails.
-- Then re-apply roster_filtered_views.sql (CREATE OR REPLACE on all *_roster views).

DROP VIEW IF EXISTS public.catapult_stats_staging_roster CASCADE;

ALTER TABLE public.athlete_identity
    ALTER COLUMN gymaware_athlete_reference TYPE BIGINT
    USING gymaware_athlete_reference::bigint;
