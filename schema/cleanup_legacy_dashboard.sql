-- Remove pre-medallion dashboard experiment objects (unified wide table + vw_* layer).
-- Safe to run: nothing in Capstone-team54-volleyball-toolkit ETL references these objects.
-- Keeps: vendor staging/BI extract, roster_cohort, athlete_identity, *_roster cohort views,
--         catapult_stats_staging_flat, catapult_session_metrics (legacy narrow metrics).

-- Legacy Power BI / prototype views
DROP VIEW IF EXISTS public.vw_athlete_dashboard CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_catapult CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_gymaware CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_vald CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_whoop CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_whoop_recovery CASCADE;
DROP VIEW IF EXISTS public.vw_dashboard_whoop_sleep CASCADE;
DROP VIEW IF EXISTS public.vw_gymaware_load_velocity CASCADE;
DROP VIEW IF EXISTS public.vw_gymaware_personal_best CASCADE;

-- Superseded by BI extract + planned Gold star schema
DROP VIEW IF EXISTS public.intermediate_big_table CASCADE;
DROP VIEW IF EXISTS public.catapult_roster_from_stats CASCADE;

-- Legacy unified physical tables (replaced by *_bi_extract + roster_cohort)
DROP TABLE IF EXISTS public.dashboard_design CASCADE;
DROP TABLE IF EXISTS public.raw_datas CASCADE;
DROP TABLE IF EXISTS public.athlete_info CASCADE;
