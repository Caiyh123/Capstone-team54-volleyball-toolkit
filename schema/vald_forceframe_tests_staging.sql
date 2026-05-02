-- External ForceFrame API — GET /tests/v2 (per tenant, optional profile filter).
-- Append-only raw layer: one row per ingested test summary (metrics live in payload JSONB).
-- Apply after medallion pattern is understood; same DATABASE_URL + VALD OAuth as profiles.

CREATE TABLE IF NOT EXISTS public.vald_forceframe_tests_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    test_id UUID NOT NULL,
    profile_id UUID,
    test_date_utc TIMESTAMPTZ,
    test_type_name TEXT,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vald_ff_tests_tenant_test
    ON public.vald_forceframe_tests_staging (tenant_id, test_id);
CREATE INDEX IF NOT EXISTS idx_vald_ff_tests_profile
    ON public.vald_forceframe_tests_staging (tenant_id, profile_id);
CREATE INDEX IF NOT EXISTS idx_vald_ff_tests_test_date
    ON public.vald_forceframe_tests_staging (test_date_utc DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_vald_ff_tests_etl
    ON public.vald_forceframe_tests_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.vald_forceframe_tests_staging IS
    'VALD External ForceFrame API test summaries (GET /tests/v2). Join profile_id to vald_profiles / roster.';

COMMENT ON COLUMN public.vald_forceframe_tests_staging.payload IS
    'Full GetTestSummaryResponseV2 object: forces, impulses, testTypeName, device, etc.';
