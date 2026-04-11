-- WHOOP OAuth tokens after browser consent (Auth Bridge callback).
-- Lock down with RLS: only service role / backend should read refresh_token; BI uses views without tokens.

CREATE TABLE IF NOT EXISTS public.whoop_oauth_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_label TEXT,
    whoop_user_id TEXT NOT NULL,
    refresh_token TEXT,
    access_token TEXT,
    expires_at TIMESTAMPTZ,
    scope TEXT,
    raw_token_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    needs_reconnect BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT whoop_oauth_token_whoop_user_unique UNIQUE (whoop_user_id)
);

CREATE INDEX IF NOT EXISTS idx_whoop_oauth_state_label ON public.whoop_oauth_token (state_label);

COMMENT ON TABLE public.whoop_oauth_token IS
    'Per-WHOOP-user tokens from OAuth; nightly ETL refreshes access_token using refresh_token.';
