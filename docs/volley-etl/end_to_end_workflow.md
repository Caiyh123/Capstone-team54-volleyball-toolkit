# End-to-end workflow (going forward)

This ties together the **headless** plan: **Supabase** + **Python** + **Power BI**, **WHOOP via Render OAuth bridge**, and existing **Catapult / GymAware** pipelines. Adjust names (Render URL, table names) to match your implementation.

---

## Big picture

```text
[Sources]                    [Ingestion]                 [Warehouse]           [Consumers]
Catapult, GymAware    →     Python scripts (cron)  →     Supabase Postgres  →     Power BI (scheduled refresh)
VALD (later)          →     Python scripts (cron)  →

WHOOP                 →     ① One-time: athlete clicks link (browser)
                      →     ② Render app exchanges code → stores refresh_token in Supabase
                      →     ③ Nightly: cron refreshes token → pulls metrics → UPSERT whoop_metrics
                      →     Supabase  →  Power BI
```

**You are not building** a full athlete web app. You **are** building a **small HTTPS “Auth Bridge”** on Render **only** because WHOOP requires a **browser once per athlete** for OAuth.

---

## Phase A — One-time setup (you / dev / IT)

| Step | What happens |
|------|----------------|
| A1 | **WHOOP Developer app** created: Client ID, Client Secret, requested **scopes** (e.g. recovery, sleep, cycles, workout — only what you need) + **`offline`** for refresh tokens. |
| A2 | **Redirect URI** registered in WHOOP = **exact URL** of your Render callback route, e.g. `https://<your-service>.onrender.com/callback` (must match deployed code). |
| A3 | **Supabase** project: tables for athletes, `whoop_metrics`, RLS so **only backend** (service role) reads `refresh_token`; Power BI uses **read-only** role or views **without** tokens. |
| A4 | **Render** (or similar): deploy **FastAPI Auth Bridge** (HTTPS). |
| A5 | **Master athlete list**: `sasi_id` (or internal id) ↔ names ↔ GymAware IDs (Excel done); **Vish** supplies other reference ids as needed. |

---

## Phase B — Per-athlete WHOOP connection (one-time each, ~16 people)

| Step | Who | What happens |
|------|-----|----------------|
| B1 | You | Generate **personal links**: each link hits your bridge, e.g. `https://<render>/login?token=<signed_one_time>` (not raw `sasi_id` in URL if you can avoid it). |
| B2 | Client | Emails/SMS **one link per athlete**. |
| B3 | Athlete | Clicks link → redirected to **WHOOP login** → approves your app. |
| B4 | WHOOP | Redirects browser to **your Redirect URI** with `?code=...&state=...`. |
| B5 | Render bridge | Exchanges `code` for **access_token + refresh_token**, reads `state` to know which athlete row to update, **UPSERT** `refresh_token` (encrypted if you implemented that) in Supabase. |
| B6 | Athlete | Sees “Success, you can close this tab” (optional). |

**After B**, that athlete never needs to log in again for routine syncs — until they **revoke** access or tokens break.

---

## Phase C — Nightly WHOOP ETL (automated)

| Step | When | What happens |
|------|------|----------------|
| C1 | e.g. **02:00** daily | Cron (GitHub Actions, Render cron, VM, etc.) runs **one Python script** (service role DB credentials). |
| C2 | | Load all athletes with a **valid `refresh_token`**. |
| C3 | | For each athlete **sequentially** (or with locks): refresh access token → if WHOOP returns **new refresh token**, **save it** (rotation). |
| C4 | | Call WHOOP APIs for **previous day** (or agreed window): recovery, sleep, strain, etc. |
| C5 | | **UPSERT** into `public.whoop_metrics` (or split tables). |

**Failure handling:** log errors; if refresh fails (401), mark athlete **needs_reconnect** and notify client to re-send link.

---

## Phase D — Catapult & GymAware (already in Volley repo)

| Step | When | What happens |
|------|------|----------------|
| D1 | Same or separate schedule | `bulk_export.py` → `upload_to_supabase.py` |
| D2 | | `gymaware_export.py` → `upload_gymaware_to_supabase.py` |
| D3 | Optional | Filter **GymAware** rows by **`GymAware API Reference Numbers.xlsx`** allowlist (`integrations/gymaware/allowlist.py` when wired). |
| D4 | Optional | `load_index.py` on a cadence → store or export for BI |

---

## Phase E — VALD (when SASI sends credentials)

| Step | What happens |
|------|----------------|
| E1 | Follow `docs/vald_onboarding.md` (March 2026 API changes first). |
| E2 | Add `integrations/vald/client.py` + export script + Supabase tables. |
| E3 | Add step to **scheduled sync** script (or second cron job). |

---

## Phase F — Power BI (coaches)

| Step | What happens |
|------|----------------|
| F1 | Connect Power BI **Import** to Supabase (Postgres connector or gateway per your IT rules). |
| F2 | Build **models** joining on **internal athlete id** + **date** (once mapping is complete). |
| F3 | **Scheduled refresh** e.g. **05:00** after ETL finishes (so data is fresh). |

---

## What goes where (redirect URI confusion)

| System | Redirect URI is for… |
|--------|----------------------|
| **WHOOP OAuth** | **Only** the **Render Auth Bridge** callback URL you registered — e.g. `https://<app>.onrender.com/callback`. |
| **Vercel dashboard** (if you still use it) | Separate **OAuth apps** (e.g. Microsoft login) — **not** WHOOP unless you intentionally handle WHOOP on Vercel (your current plan does **not**). |

---

## Order of operations (simple checklist)

1. [ ] Supabase schemas + athlete table + `whoop_metrics` + token column (secured).  
2. [ ] WHOOP Developer app + **Redirect URI** = Render callback.  
3. [ ] Deploy Render **Auth Bridge**; test callback with **one** test athlete.  
4. [ ] Generate **16 links**; client distributes.  
5. [ ] Deploy **nightly WHOOP ETL** cron.  
6. [ ] Keep **Catapult/GymAware** cron as today.  
7. [ ] Power BI model + scheduled refresh.  
8. [ ] VALD when ready.  

---

## Files in this repo (reference)

- `scripts/run_scheduled_sync.ps1` — Catapult + GymAware chain.  
- `backend/app.py` — WHOOP Auth Bridge (FastAPI): `/health`, `/whoop/start`, `/callback`.  
- `integrations/whoop/oauth.py` — WHOOP authorize URL + token exchange + profile `user_id`.  
- `schema/whoop_oauth_tokens.sql` — persist refresh/access tokens after OAuth callback.  
- `docs/vald_onboarding.md` — VALD reading order.  
- `docs/whoop_via_teamworks.md` — **historical** note if AMS path was considered; **current plan** is direct WHOOP.  
- `integrations/gymaware/allowlist.py` — GymAware ID allowlist from Excel.

---

*Update as Render URL and table names are finalized.*
