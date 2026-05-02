-- External ForceDecks API — GET /tests (TenantId + ModifiedFromUtc [+ ProfileId]).
-- Aligns with Volleyball AU package: VA_VALD_Tests (primary key testId).

CREATE TABLE IF NOT EXISTS public.vald_forcedecks_tests_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    test_id UUID NOT NULL,
    profile_id UUID,
    recording_id UUID,
    test_type TEXT,
    modified_date_utc TIMESTAMPTZ,
    recorded_date_utc TIMESTAMPTZ,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vald_fd_tests_tenant_test
    ON public.vald_forcedecks_tests_staging (tenant_id, test_id);
CREATE INDEX IF NOT EXISTS idx_vald_fd_tests_profile
    ON public.vald_forcedecks_tests_staging (profile_id);
CREATE INDEX IF NOT EXISTS idx_vald_fd_tests_etl
    ON public.vald_forcedecks_tests_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.vald_forcedecks_tests_staging IS
    'VALD External ForceDecks GET /tests (TestResponse). See Package_Volleyball_AU_UniA/data README.';
