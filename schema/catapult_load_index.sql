-- Load Index from load_index.py (sum(total_player_load) / jump count from basketball events).
-- Matches JSON shape written to load_index_result.json (see load_index.py).
--
-- Paste ONLY this file into the Supabase SQL editor (not upload_load_index_to_supabase.py).
-- After tables exist: python upload_load_index_to_supabase.py (from repo root, with DATABASE_URL).

CREATE TABLE IF NOT EXISTS public.catapult_load_index_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    sum_player_load DOUBLE PRECISION NOT NULL,
    total_jump_count INTEGER NOT NULL DEFAULT 0,
    load_index DOUBLE PRECISION,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catapult_load_index_run_dates
    ON public.catapult_load_index_run (start_date, end_date DESC);

CREATE INDEX IF NOT EXISTS idx_catapult_load_index_run_synced
    ON public.catapult_load_index_run (synced_at DESC);

COMMENT ON TABLE public.catapult_load_index_run IS
    'One row per load_index.py run: aggregate Load Index over UTC date window.';

CREATE TABLE IF NOT EXISTS public.catapult_load_index_activity (
    run_id UUID NOT NULL REFERENCES public.catapult_load_index_run (id) ON DELETE CASCADE,
    activity_id UUID NOT NULL,
    activity_name TEXT,
    sum_player_load DOUBLE PRECISION NOT NULL,
    jump_count INTEGER NOT NULL DEFAULT 0,
    load_index_local DOUBLE PRECISION,
    PRIMARY KEY (run_id, activity_id)
);

CREATE INDEX IF NOT EXISTS idx_catapult_load_index_activity_activity_id
    ON public.catapult_load_index_activity (activity_id);

COMMENT ON TABLE public.catapult_load_index_activity IS
    'Per-activity breakdown for a load index run (local index = load/jumps when jumps > 0).';
