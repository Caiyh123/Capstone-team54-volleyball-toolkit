-- Latest Catapult roster fields per logical athlete from stats_payload.
-- Run after catapult_stats_staging.sql AND schema/roster_filtered_views.sql (uses catapult_stats_staging_roster).
-- Complements athlete_identity (manual crosswalk).
--
-- IMPORTANT: catapult_stats_staging.athlete_key is COALESCE(athlete_id, zero-uuid). When
-- athlete_id is NULL for every row, athlete_key is identical for all rows, so DISTINCT ON
-- (athlete_key) would return a single row. We dedupe using roster_key below instead.
--
-- This is a VIEW (not a physical table). For a snapshot table:
--   CREATE TABLE public.catapult_roster_snapshot AS SELECT * FROM public.catapult_roster_from_stats;

CREATE OR REPLACE VIEW public.catapult_roster_from_stats
WITH (security_invoker = true)
AS
SELECT
    athlete_id,
    athlete_key,
    team_name,
    position_name,
    athlete_jersey,
    last_synced_at
FROM (
    SELECT DISTINCT ON (roster_key)
        s.athlete_id,
        s.athlete_key,
        (s.stats_payload->>'team_name') AS team_name,
        (s.stats_payload->>'position_name') AS position_name,
        (s.stats_payload->>'athlete_jersey') AS athlete_jersey,
        s.synced_at AS last_synced_at,
        roster_key
    FROM (
        SELECT
            s.*,
            COALESCE(
                CASE WHEN s.athlete_id IS NOT NULL THEN s.athlete_id::text END,
                NULLIF(btrim(s.stats_payload->'participating_athlete'->>'id'), ''),
                NULLIF(NULLIF(btrim(s.stats_payload->>'participating_athlete_id'), ''), '0'),
                NULLIF(btrim(s.stats_payload->>'source_activity_id'), ''),
                CASE
                    WHEN (s.stats_payload->>'team_name') IS NOT NULL
                      OR (s.stats_payload->>'athlete_jersey') IS NOT NULL
                      OR (s.stats_payload->>'position_name') IS NOT NULL
                    THEN concat_ws(
                        E'\x01',
                        COALESCE(s.stats_payload->>'team_name', ''),
                        COALESCE(s.stats_payload->>'athlete_jersey', ''),
                        COALESCE(s.stats_payload->>'position_name', '')
                    )
                END,
                s.activity_id::text
            ) AS roster_key
        FROM public.catapult_stats_staging_roster s
    ) s
    ORDER BY roster_key, s.synced_at DESC, s.activity_id DESC
) x;

COMMENT ON VIEW public.catapult_roster_from_stats IS
    'Cohort-scoped: built from catapult_stats_staging_roster. Latest team_name, position_name, athlete_jersey per roster_key.';
