-- Intermediate "big table" for Power BI: one row per Catapult stats row (append-only grain),
-- joined to athlete_identity + roster_cohort, latest VALD profile row, same-day GymAware summaries,
-- and same-day WHOOP sleep when whoop_user_id is mapped in athlete_identity.
--
-- Identity resolution (matches roster_filtered_views / catapult_stats_staging_roster):
--   1) Catapult athlete UUID -> athlete_identity.catapult_athlete_id
--   2) Else stats_payload.athlete_jersey -> roster_cohort.catapult_jersey -> athlete_identity via gymaware ref
-- Roster + VALD/GymAware can resolve from roster_cohort alone when athlete_identity is missing a UUID but
-- jersey matches roster (VALD profile id on roster row).
--
-- Rows are limited to the approved cohort (in roster via UUID path OR jersey path). Sessions with no
-- roster match (e.g. empty jersey and no resolvable UUID in cohort) are excluded so non-Catapult-only
-- roster members and stray sessions do not appear.
--
-- Prerequisites: medallion_raw_layer_migration.sql, athlete_identity.sql, roster_cohort.sql, vendor staging.

-- Postgres: replacing this view may require drop if column list changes.
DROP VIEW IF EXISTS public.intermediate_big_table CASCADE;

CREATE VIEW public.intermediate_big_table
WITH (security_invoker = true)
AS
SELECT
    cs.ingest_id AS catapult_ingest_id,
    cs.etl_ingested_at AS catapult_etl_ingested_at,
    cs.activity_id AS catapult_activity_id,
    cs.athlete_id AS catapult_athlete_id,
    (cs.stats_payload->>'date') AS catapult_stats_date_text,
    (cs.stats_payload->>'start_time')::double precision AS catapult_start_time_epoch,
    (cs.stats_payload->>'total_player_load')::double precision AS catapult_total_player_load,
    (cs.stats_payload->>'total_distance')::double precision AS catapult_total_distance,
    (cs.stats_payload->>'field_time')::double precision AS catapult_field_time,
    (cs.stats_payload->>'athlete_jersey') AS catapult_athlete_jersey,
    d.cal_date AS activity_calendar_date,

    ai.id AS athlete_identity_id,
    ai.internal_key AS athlete_internal_key,
    ai.display_name AS athlete_display_name,
    COALESCE(ai.gymaware_athlete_reference, rc.gymaware_athlete_reference) AS gymaware_athlete_reference,
    COALESCE(ai.vald_profile_id, rc.vald_profile_id) AS vald_profile_id,
    ai.whoop_user_id,

    rc.display_label AS roster_display_label,
    rc.catapult_jersey AS roster_catapult_jersey,

    vp.given_name AS vald_given_name,
    vp.family_name AS vald_family_name,
    vp.email AS vald_email,
    vp.date_of_birth AS vald_date_of_birth,
    vp.etl_ingested_at AS vald_profile_etl_ingested_at,

    ga.gymaware_sets_json,

    ws.whoop_sleep_payload,
    ws.whoop_sleep_etl_ingested_at,

    cs.stats_payload AS catapult_stats_payload
FROM public.catapult_stats_staging cs
CROSS JOIN LATERAL (
    SELECT
        COALESCE(
            CASE
                WHEN cs.stats_payload->>'date' IS NOT NULL
                     AND btrim(cs.stats_payload->>'date') <> ''
                     AND btrim(cs.stats_payload->>'date') ~ '^\d{4}-\d{2}-\d{2}$' THEN
                    btrim(cs.stats_payload->>'date')::date
                ELSE NULL
            END,
            CASE
                WHEN cs.stats_payload->>'start_time' IS NOT NULL
                     AND (cs.stats_payload->>'start_time')::double precision > 0 THEN
                    (
                        to_timestamp((cs.stats_payload->>'start_time')::double precision)
                        AT TIME ZONE 'UTC'
                    )::date
                ELSE NULL
            END
        ) AS cal_date
) d
LEFT JOIN LATERAL (
    SELECT a.*
    FROM public.athlete_identity a
    WHERE (
        cs.athlete_id IS NOT NULL
        AND a.catapult_athlete_id IS NOT NULL
        AND btrim(a.catapult_athlete_id) <> ''
        AND cs.athlete_id::text = btrim(a.catapult_athlete_id)
    )
    OR (
        a.gymaware_athlete_reference IN (
            SELECT r.gymaware_athlete_reference
            FROM public.roster_cohort r
            WHERE r.catapult_jersey IS NOT NULL
              AND btrim(r.catapult_jersey) <> ''
              AND btrim(cs.stats_payload->>'athlete_jersey') <> ''
              AND lower(btrim(r.catapult_jersey)) = lower(btrim(cs.stats_payload->>'athlete_jersey'))
        )
    )
    ORDER BY
        CASE
            WHEN cs.athlete_id IS NOT NULL
                 AND a.catapult_athlete_id IS NOT NULL
                 AND cs.athlete_id::text = btrim(a.catapult_athlete_id)
            THEN 0
            ELSE 1
        END
    LIMIT 1
) ai ON TRUE
LEFT JOIN LATERAL (
    SELECT r.*
    FROM public.roster_cohort r
    WHERE (
        ai.id IS NOT NULL
        AND ai.gymaware_athlete_reference IS NOT NULL
        AND r.gymaware_athlete_reference = ai.gymaware_athlete_reference
    )
    OR (
        btrim(cs.stats_payload->>'athlete_jersey') <> ''
        AND r.catapult_jersey IS NOT NULL
        AND btrim(r.catapult_jersey) <> ''
        AND lower(btrim(r.catapult_jersey)) = lower(btrim(cs.stats_payload->>'athlete_jersey'))
    )
    LIMIT 1
) rc ON TRUE
LEFT JOIN LATERAL (
    SELECT v.given_name, v.family_name, v.email, v.date_of_birth, v.etl_ingested_at
    FROM public.vald_profiles v
    WHERE COALESCE(btrim(ai.vald_profile_id), btrim(rc.vald_profile_id)) IS NOT NULL
      AND btrim(COALESCE(ai.vald_profile_id, rc.vald_profile_id)) <> ''
      AND lower(btrim(v.profile_id)) = lower(btrim(COALESCE(ai.vald_profile_id, rc.vald_profile_id)))
    ORDER BY v.etl_ingested_at DESC NULLS LAST
    LIMIT 1
) vp ON TRUE
LEFT JOIN LATERAL (
    SELECT jsonb_agg(
        jsonb_build_object(
            'gymaware_reference', g.gymaware_reference,
            'recorded', g.recorded,
            'exercise_name', g.exercise_name,
            'mean_power', g.mean_power,
            'peak_velocity', g.peak_velocity,
            'etl_ingested_at', g.etl_ingested_at
        )
        ORDER BY g.etl_ingested_at DESC
    ) AS gymaware_sets_json
    FROM public.gymaware_summaries g
    WHERE d.cal_date IS NOT NULL
      AND COALESCE(ai.gymaware_athlete_reference, rc.gymaware_athlete_reference) IS NOT NULL
      AND g.athlete_reference IS NOT NULL
      AND trim(g.athlete_reference) ~ '^[0-9]+$'
      AND g.athlete_reference::bigint = COALESCE(ai.gymaware_athlete_reference, rc.gymaware_athlete_reference)
      AND date_trunc(
          'day',
          to_timestamp(
              CASE
                  WHEN g.recorded IS NULL THEN NULL::double precision
                  WHEN g.recorded > 1e12 THEN g.recorded / 1000.0
                  ELSE g.recorded
              END
          ) AT TIME ZONE 'UTC'
      )::date = d.cal_date
) ga ON TRUE
LEFT JOIN LATERAL (
    SELECT sl.payload AS whoop_sleep_payload, sl.etl_ingested_at AS whoop_sleep_etl_ingested_at
    FROM public.whoop_sleep_staging sl
    WHERE d.cal_date IS NOT NULL
      AND ai.whoop_user_id IS NOT NULL
      AND btrim(ai.whoop_user_id) <> ''
      AND sl.whoop_user_id = ai.whoop_user_id
      AND (sl.payload->>'start') IS NOT NULL
      AND date_trunc('day', (sl.payload->>'start')::timestamptz AT TIME ZONE 'UTC')::date = d.cal_date
    ORDER BY sl.etl_ingested_at DESC
    LIMIT 1
) ws ON TRUE
WHERE (
    EXISTS (
        SELECT 1
        FROM public.athlete_identity ai2
        INNER JOIN public.roster_cohort r
          ON ai2.gymaware_athlete_reference = r.gymaware_athlete_reference
        WHERE ai2.catapult_athlete_id IS NOT NULL
          AND btrim(ai2.catapult_athlete_id) <> ''
          AND cs.athlete_id IS NOT NULL
          AND cs.athlete_id::text = btrim(ai2.catapult_athlete_id)
    )
    OR EXISTS (
        SELECT 1
        FROM public.roster_cohort r2
        WHERE r2.catapult_jersey IS NOT NULL
          AND btrim(r2.catapult_jersey) <> ''
          AND btrim(cs.stats_payload->>'athlete_jersey') <> ''
          AND lower(btrim(cs.stats_payload->>'athlete_jersey')) = lower(btrim(r2.catapult_jersey))
    )
);

COMMENT ON VIEW public.intermediate_big_table IS
    'Intermediate layer: Catapult row + identity/roster (UUID or jersey) + VALD + GymAware + WHOOP sleep; cohort-scoped.';
