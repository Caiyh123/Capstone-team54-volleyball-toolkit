# Deploy WHOOP Auth Bridge on Render

This deploys only the **FastAPI** app in `backend/app.py` (WHOOP OAuth callback + health check). Catapult/GymAware scripts are not run on Render unless you add a separate **Background Worker** or **Cron** later.

## Prerequisites

- GitHub repo connected to Render (this project).
- **Supabase:** `schema/whoop_oauth_tokens.sql` applied.
- **WHOOP Developer Dashboard:** app created (you will add the redirect URI **after** you know the public URL).

## Option A — Blueprint (`render.yaml`)

1. Push `render.yaml` to your default branch.
2. In Render: **Blueprints** → **New Blueprint Instance** → select the repository.
3. Apply the blueprint. When prompted, enter:
   - `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`
   - `DATABASE_URL` (Supabase **Settings → Database → Connection string**; use URI that allows Render’s egress, often the **pooler** with `?sslmode=require` if required)
4. Open the new **Web Service** → note the URL, e.g. `https://whoop-auth-bridge.onrender.com`.
5. Set **`WHOOP_REDIRECT_URI`** in Render **Environment** to exactly:
   ```text
   https://whoop-auth-bridge.onrender.com/callback
   ```
   (Replace with your real hostname.)
6. In the **WHOOP Developer Dashboard**, add the **same** URL under Redirect URIs.
7. **Manual Deploy** → **Clear build cache & deploy** if the service was created before `WHOOP_REDIRECT_URI` was correct (usually a simple restart is enough after env change).

**Smoke test:** `GET https://<your-host>/health` → `{"status":"ok"}`.

**Athlete link format:**  
`https://<your-host>/whoop/start?state=<at-least-8-chars>`  
Example: `?state=athlete001234`

## Option B — Web Service manually (no Blueprint)

1. **New** → **Web Service** → connect repo.
2. **Runtime:** Python  
3. **Build command:** `pip install -r requirements.txt`  
4. **Start command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`  
5. **Health check path:** `/health`  
6. Add the same environment variables as in Option A.

## Handover checklist

| Item | Owner |
|------|--------|
| Render service URL | Document in client runbook |
| WHOOP app Client ID (not secret) | Client-visible if they own the dashboard |
| Redirect URI registered in WHOOP | Must match `WHOOP_REDIRECT_URI` |
| `DATABASE_URL` rotation | Supabase / IT |
| Who sends athlete links | Staff email/SMS policy |

## Troubleshooting

- **502 on `/callback`:** DB URL wrong, or `whoop_oauth_tokens` table missing, or Supabase firewall blocking Render (allow **0.0.0.0/0** on Supabase pooler for serverless, or use [Supabase network restrictions](https://supabase.com/docs/guides/platform/network-restrictions) as your policy allows).
- **Token exchange fails:** `WHOOP_REDIRECT_URI` must match **character-for-character** what was used in `/whoop/start` flow and in WHOOP dashboard (including `https`, no trailing slash on domain unless you registered it).
- **No refresh token:** Ensure `offline` is included in scopes (`WHOOP_SCOPES` in `.env` / Render env).
