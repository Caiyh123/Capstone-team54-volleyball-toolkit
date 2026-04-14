-- Optional: flatten selected keys from stats_payload for SQL-friendly queries.
-- Run after catapult_stats_staging.sql. Re-run after changing column list.
-- The base table keeps the full JSONB; this view adds no storage (computed at read time).

-- security_invoker: enforce caller's privileges and RLS on catapult_stats_staging (not the view owner).
CREATE OR REPLACE VIEW public.catapult_stats_staging_flat
WITH (security_invoker = true)
AS
SELECT
    s.activity_id,
    s.athlete_id,
    s.athlete_key,
    s.synced_at,

    (s.stats_payload->>'date_id') AS date_id,
    (s.stats_payload->>'date_name') AS date_name,
    (s.stats_payload->>'date') AS stats_date,
    (s.stats_payload->>'activity_name') AS activity_name,
    (s.stats_payload->>'period_name') AS period_name,
    (s.stats_payload->>'team_name') AS team_name,
    (s.stats_payload->>'position_name') AS position_name,
    (s.stats_payload->>'athlete_jersey') AS athlete_jersey,

    (s.stats_payload->>'start_time')::double precision AS start_time,
    (s.stats_payload->>'end_time')::double precision AS end_time,
    (s.stats_payload->>'field_time')::double precision AS field_time,
    (s.stats_payload->>'bench_time')::double precision AS bench_time,
    (s.stats_payload->>'total_distance')::double precision AS total_distance,
    (s.stats_payload->>'total_duration')::double precision AS total_duration,
    (s.stats_payload->>'total_player_load')::double precision AS total_player_load,
    (s.stats_payload->>'peak_player_load')::double precision AS peak_player_load,
    (s.stats_payload->>'total_2d_player_load')::double precision AS total_2d_player_load,
    (s.stats_payload->>'max_vel')::double precision AS max_vel,
    (s.stats_payload->>'max_heart_rate')::double precision AS max_heart_rate,
    (s.stats_payload->>'min_heart_rate')::double precision AS min_heart_rate,
    (s.stats_payload->>'hsr')::double precision AS hsr,
    (s.stats_payload->>'velocity_exertion')::double precision AS velocity_exertion,
    (s.stats_payload->>'heart_rate_exertion')::double precision AS heart_rate_exertion,
    (s.stats_payload->>'equivalent_distance')::double precision AS equivalent_distance,
    (s.stats_payload->>'total_acceleration_load')::double precision AS total_acceleration_load,

    (s.stats_payload->>'is_injected')::boolean AS is_injected,
    (s.stats_payload->>'is_demo_data')::boolean AS is_demo_data,
    (s.stats_payload->>'athlete_weight')::double precision AS athlete_weight,

    (s.stats_payload->'participating_athlete'->>'id')::uuid AS participating_athlete_id,
    (s.stats_payload->>'source_activity_id')::uuid AS source_activity_id,

    s.stats_payload
FROM public.catapult_stats_staging s;

COMMENT ON VIEW public.catapult_stats_staging_flat IS
    'Convenience view: common scalar fields extracted from stats_payload; full document remains in stats_payload.';
