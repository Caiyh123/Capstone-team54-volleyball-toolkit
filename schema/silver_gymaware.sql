-- Silver GymAware views: dedupe append-only BI rows; roster athlete_internal_key + athlete_display_name.
--
-- Bronze gymaware_*_bi_extract may contain duplicate ingests per natural key.
-- Join athlete_identity on gymaware_athlete_reference (from roster_new.xlsx sync).
--
-- Power BI: use silver_* views for GymAware pages and slicers on athlete_display_name.

DROP VIEW IF EXISTS public.silver_gymaware_bests CASCADE;
DROP VIEW IF EXISTS public.silver_gymaware_athletes CASCADE;
DROP VIEW IF EXISTS public.silver_gymaware_rep CASCADE;
DROP VIEW IF EXISTS public.silver_gymaware_summaries CASCADE;

-- ---------------------------------------------------------------------------
-- Summaries (sets)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_gymaware_summaries
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (g.gymaware_reference)
    g.id,
    g.source_staging_id,
    g.gymaware_reference,
    g.recorded,
    g.modified,
    g.athlete_reference,
    g.athlete_name,
    g.athlete_weight,
    g.exercise_name,
    g.exercise_reference,
    g.bar_weight,
    g.rep_count,
    g.height,
    g.dip,
    g.mean_velocity,
    g.peak_velocity,
    g.mean_power,
    g.peak_power,
    g.mean_watts_per_kg,
    g.peak_watts_per_kg,
    g.velocity_zone,
    g.activity_name,
    g.activity_reference,
    g.sensor,
    g.hardware,
    g.notes,
    g.deleted,
    g.targets_mode,
    g.targets_analysis,
    g.targets_best_max,
    g.targets_best_min,
    g.targets_last_max,
    g.targets_last_min,
    g.targets_squad_max,
    g.targets_squad_min,
    g.targets_preset_max,
    g.targets_preset_min,
    g.vendor_synced_at,
    g.etl_ingested_at,
    CASE
        WHEN g.recorded IS NOT NULL AND g.recorded > 0 THEN
            (to_timestamp(g.recorded) AT TIME ZONE 'UTC')::date
        ELSE NULL
    END AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    COALESCE(ai.display_name, g.athlete_name) AS athlete_display_name
FROM public.gymaware_summaries_bi_extract g
LEFT JOIN public.athlete_identity ai
    ON g.athlete_reference IS NOT NULL
   AND trim(g.athlete_reference) ~ '^[0-9]+$'
   AND ai.gymaware_athlete_reference = trim(g.athlete_reference)::bigint
ORDER BY g.gymaware_reference, g.etl_ingested_at DESC, g.id DESC;

COMMENT ON VIEW public.silver_gymaware_summaries IS
    'One row per GymAware set (gymaware_reference); deduped + roster athlete names.';

-- ---------------------------------------------------------------------------
-- Reps (one row per rep)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_gymaware_rep
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (r.set_reference, r.rep_num)
    r.id,
    r.source_staging_ingest_id,
    r.set_reference,
    r.rep_num,
    r.recorded,
    r.modified,
    r.athlete_reference,
    r.athlete_name,
    r.athlete_weight,
    r.exercise_name,
    r.exercise_reference,
    r.bar_weight,
    r.rep_count,
    r.activity_name,
    r.activity_reference,
    r.rep_metrics,
    r.vendor_synced_at,
    r.etl_ingested_at,
    CASE
        WHEN r.recorded IS NOT NULL AND r.recorded > 0 THEN
            (to_timestamp(r.recorded) AT TIME ZONE 'UTC')::date
        ELSE NULL
    END AS calendar_date,
    ai.internal_key AS athlete_internal_key,
    COALESCE(ai.display_name, r.athlete_name) AS athlete_display_name
FROM public.gymaware_rep_bi_extract r
LEFT JOIN public.athlete_identity ai
    ON r.athlete_reference IS NOT NULL
   AND trim(r.athlete_reference) ~ '^[0-9]+$'
   AND ai.gymaware_athlete_reference = trim(r.athlete_reference)::bigint
ORDER BY r.set_reference, r.rep_num, r.etl_ingested_at DESC, r.id DESC;

COMMENT ON VIEW public.silver_gymaware_rep IS
    'One row per rep; deduped + roster athlete names.';

-- ---------------------------------------------------------------------------
-- Athletes (profile snapshot)
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_gymaware_athletes
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (a.athlete_reference)
    a.id,
    a.source_staging_ingest_id,
    a.athlete_reference,
    a.display_name AS gymaware_display_name,
    a.first_name,
    a.last_name,
    a.jersey_number,
    a.position,
    a.sport,
    a.address,
    a.phone,
    a.born,
    a.photo,
    a.modified,
    a.vendor_synced_at,
    a.etl_ingested_at,
    ai.internal_key AS athlete_internal_key,
    COALESCE(ai.display_name, a.display_name, trim(concat(a.last_name, ', ', a.first_name), ', '))
        AS athlete_display_name
FROM public.gymaware_athletes_bi_extract a
LEFT JOIN public.athlete_identity ai
    ON a.athlete_reference IS NOT NULL
   AND trim(a.athlete_reference) ~ '^[0-9]+$'
   AND ai.gymaware_athlete_reference = trim(a.athlete_reference)::bigint
ORDER BY a.athlete_reference, a.etl_ingested_at DESC, a.id DESC;

COMMENT ON VIEW public.silver_gymaware_athletes IS
    'One row per GymAware athlete profile; roster internal_key + display_name.';

-- ---------------------------------------------------------------------------
-- Personal bests
-- ---------------------------------------------------------------------------
CREATE VIEW public.silver_gymaware_bests
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (
    COALESCE(b.athlete_reference, ''),
    COALESCE(b.exercise_name, ''),
    COALESCE(b.bar_weight::text, '')
)
    b.id,
    b.source_staging_ingest_id,
    b.athlete_reference,
    b.athlete_name,
    b.exercise_name,
    b.bar_weight,
    b.height,
    b.dip,
    b.mean_velocity,
    b.peak_velocity,
    b.mean_power,
    b.peak_power,
    b.mean_watts_per_kg,
    b.peak_watts_per_kg,
    b.vendor_synced_at,
    b.etl_ingested_at,
    ai.internal_key AS athlete_internal_key,
    COALESCE(ai.display_name, b.athlete_name) AS athlete_display_name
FROM public.gymaware_bests_bi_extract b
LEFT JOIN public.athlete_identity ai
    ON b.athlete_reference IS NOT NULL
   AND trim(b.athlete_reference) ~ '^[0-9]+$'
   AND ai.gymaware_athlete_reference = trim(b.athlete_reference)::bigint
ORDER BY
    COALESCE(b.athlete_reference, ''),
    COALESCE(b.exercise_name, ''),
    COALESCE(b.bar_weight::text, ''),
    b.etl_ingested_at DESC,
    b.id DESC;

COMMENT ON VIEW public.silver_gymaware_bests IS
    'One row per athlete + exercise + bar_weight best; deduped + roster names.';
