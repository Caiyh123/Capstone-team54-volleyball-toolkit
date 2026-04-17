-- Read-scoped views: only data for athletes in public.roster_cohort.
-- Apply after roster_cohort.sql, athlete_identity.sql, and vendor staging tables.

-- GymAware summaries (athlete_reference is TEXT digits)
CREATE OR REPLACE VIEW public.gymaware_summaries_roster AS
SELECT g.*
FROM public.gymaware_summaries g
INNER JOIN public.roster_cohort r
  ON trim(g.athlete_reference) ~ '^[0-9]+$'
 AND g.athlete_reference::bigint = r.gymaware_athlete_reference;

COMMENT ON VIEW public.gymaware_summaries_roster IS
    'gymaware_summaries restricted to roster_cohort GymAware IDs.';

-- VALD profiles
CREATE OR REPLACE VIEW public.vald_profiles_roster AS
SELECT v.*
FROM public.vald_profiles v
INNER JOIN public.roster_cohort r
  ON r.vald_profile_id IS NOT NULL
 AND lower(trim(v.profile_id)) = lower(trim(r.vald_profile_id));

COMMENT ON VIEW public.vald_profiles_roster IS
    'vald_profiles restricted to roster_cohort profile IDs.';

-- Catapult stats: UUID path (athlete_identity) OR jersey path (stats_payload.athlete_jersey + roster_cohort.catapult_jersey)
-- UUID may be only in JSON (participating_athlete.id) while c.athlete_id is NULL — match both like integrations/catapult/stats_row.py.
CREATE OR REPLACE VIEW public.catapult_stats_staging_roster AS
SELECT c.*
FROM public.catapult_stats_staging c
WHERE EXISTS (
    SELECT 1
    FROM public.athlete_identity ai
    INNER JOIN public.roster_cohort r
      ON ai.gymaware_athlete_reference = r.gymaware_athlete_reference
    WHERE ai.catapult_athlete_id IS NOT NULL
      AND btrim(ai.catapult_athlete_id) <> ''
      AND (
        (
            c.athlete_id IS NOT NULL
            AND c.athlete_id::text = btrim(ai.catapult_athlete_id)
        )
        OR (
            NULLIF(btrim(c.stats_payload->'participating_athlete'->>'id'), '') IS NOT NULL
            AND lower(btrim(c.stats_payload->'participating_athlete'->>'id')) = lower(btrim(ai.catapult_athlete_id))
        )
    )
)
OR EXISTS (
    SELECT 1
    FROM public.roster_cohort r2
    WHERE r2.catapult_jersey IS NOT NULL
      AND btrim(r2.catapult_jersey) <> ''
      AND btrim(c.stats_payload->>'athlete_jersey') <> ''
      AND lower(btrim(c.stats_payload->>'athlete_jersey')) = lower(btrim(r2.catapult_jersey))
);

COMMENT ON VIEW public.catapult_stats_staging_roster IS
    'catapult_stats_staging for cohort: UUID via athlete_identity (column or participating_athlete.id in payload), or jersey via stats_payload + roster_cohort.catapult_jersey.';

-- WHOOP staging: token state_label must match roster GymAware ID (OAuth start link)
CREATE OR REPLACE VIEW public.whoop_sleep_staging_roster AS
SELECT w.*
FROM public.whoop_sleep_staging w
WHERE EXISTS (
    SELECT 1
    FROM public.whoop_oauth_token t
    INNER JOIN public.roster_cohort r
      ON t.state_label IS NOT NULL
     AND trim(t.state_label) ~ '^[0-9]+$'
     AND t.state_label::bigint = r.gymaware_athlete_reference
    WHERE t.whoop_user_id = w.whoop_user_id
);

CREATE OR REPLACE VIEW public.whoop_workout_staging_roster AS
SELECT w.*
FROM public.whoop_workout_staging w
WHERE EXISTS (
    SELECT 1
    FROM public.whoop_oauth_token t
    INNER JOIN public.roster_cohort r
      ON t.state_label IS NOT NULL
     AND trim(t.state_label) ~ '^[0-9]+$'
     AND t.state_label::bigint = r.gymaware_athlete_reference
    WHERE t.whoop_user_id = w.whoop_user_id
);

CREATE OR REPLACE VIEW public.whoop_cycle_staging_roster AS
SELECT w.*
FROM public.whoop_cycle_staging w
WHERE EXISTS (
    SELECT 1
    FROM public.whoop_oauth_token t
    INNER JOIN public.roster_cohort r
      ON t.state_label IS NOT NULL
     AND trim(t.state_label) ~ '^[0-9]+$'
     AND t.state_label::bigint = r.gymaware_athlete_reference
    WHERE t.whoop_user_id = w.whoop_user_id
);

CREATE OR REPLACE VIEW public.whoop_recovery_staging_roster AS
SELECT w.*
FROM public.whoop_recovery_staging w
WHERE EXISTS (
    SELECT 1
    FROM public.whoop_oauth_token t
    INNER JOIN public.roster_cohort r
      ON t.state_label IS NOT NULL
     AND trim(t.state_label) ~ '^[0-9]+$'
     AND t.state_label::bigint = r.gymaware_athlete_reference
    WHERE t.whoop_user_id = w.whoop_user_id
);

COMMENT ON VIEW public.whoop_sleep_staging_roster IS
    'WHOOP sleep rows for cohort (whoop_oauth_token.state_label = GymAware roster ID).';
