-- Run in Supabase: Dashboard → SQL → New query → Run
-- External Profiles API — GET /profiles (per tenant). Upsert on (tenant_id, profile_id).
-- Product metrics (ForceDecks, NordBord, etc.) belong in separate tables when you ingest those APIs.

CREATE TABLE IF NOT EXISTS public.vald_profiles (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    sync_id TEXT,
    given_name TEXT,
    family_name TEXT,
    date_of_birth TIMESTAMPTZ,
    external_id TEXT,
    email TEXT,
    group_id TEXT,
    being_merged_with_profile_id TEXT,
    being_merged_with_expiry_utc TIMESTAMPTZ,
    raw JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT vald_profiles_tenant_profile_uq UNIQUE (tenant_id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_vald_profiles_tenant ON public.vald_profiles (tenant_id);
CREATE INDEX IF NOT EXISTS idx_vald_profiles_sync_id ON public.vald_profiles (tenant_id, sync_id);
CREATE INDEX IF NOT EXISTS idx_vald_profiles_external_id ON public.vald_profiles (tenant_id, external_id);

COMMENT ON TABLE public.vald_profiles IS
    'VALD External Profiles API; one row per profile per tenant. Aligns athlete_identity.vald_profile_id with profile_id.';
