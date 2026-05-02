-- GET /resultdefinitions — metric metadata (resultId, name, unit, …).
-- Aligns with VA package: VA_VALD_Metric_Definitions / VA_VALD_MetricDef.xlsx.

CREATE TABLE IF NOT EXISTS public.vald_forcedecks_result_definitions_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vald_fd_defs_result
    ON public.vald_forcedecks_result_definitions_staging (result_id);
CREATE INDEX IF NOT EXISTS idx_vald_fd_defs_etl
    ON public.vald_forcedecks_result_definitions_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.vald_forcedecks_result_definitions_staging IS
    'VALD ForceDecks result definition catalog; join trials payload results[].resultId.';
