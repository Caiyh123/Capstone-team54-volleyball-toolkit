-- Trial-level metrics from ForceDecks DetailedTestDTO.trials (GET .../tests/detailed/...).
-- Aligns with VA package: VA_VALD_Trials (trialId, testId, resultId).

CREATE TABLE IF NOT EXISTS public.vald_forcedecks_trials_staging (
    ingest_id BIGSERIAL PRIMARY KEY,
    team_id UUID NOT NULL,
    test_id UUID NOT NULL,
    trial_id UUID NOT NULL,
    athlete_id UUID,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    etl_ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vald_fd_trials_test
    ON public.vald_forcedecks_trials_staging (team_id, test_id);
CREATE INDEX IF NOT EXISTS idx_vald_fd_trials_trial
    ON public.vald_forcedecks_trials_staging (trial_id);
CREATE INDEX IF NOT EXISTS idx_vald_fd_trials_etl
    ON public.vald_forcedecks_trials_staging (etl_ingested_at DESC);

COMMENT ON TABLE public.vald_forcedecks_trials_staging IS
    'VALD ForceDecks trials (TrialDTO) nested under detailed tests; results[] holds resultId + value.';
