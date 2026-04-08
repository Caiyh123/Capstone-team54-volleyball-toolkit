# Operations runbook

## Environment

1. Clone the repository and open the repo root in your editor.
2. Copy `.env.example` to `.env` and fill secrets (never commit `.env`).
3. Create a virtual environment and install dependencies:

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, either call `python.exe` under `.venv\Scripts\` directly or run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

4. Smoke test:

```powershell
.\.venv\Scripts\python.exe verify_integrations.py
```

Run Python from the **repository root** so `.env` and default paths (e.g. GymAware allowlist Excel) resolve correctly.

## Scheduled sync (Windows Task Scheduler)

The script `scripts/run_scheduled_sync.ps1` runs Catapult export → upload, then GymAware export → upload.

1. Set `GYMAWARE_USE_ALLOWLIST=1` in `.env` if exports must be limited to the allowlist workbook.
2. Place `GymAware API Reference Numbers.xlsx` (or set `GYMAWARE_ALLOWLIST_XLSX`) next to `.env` when allowlist is enabled.
3. Schedule **PowerShell** with execution policy bypass, pointing at this repo’s copy of the script:

```text
powershell.exe -ExecutionPolicy Bypass -File "D:\...\Capstone-team54-volleyball-toolkit\scripts\run_scheduled_sync.ps1"
```

4. Ensure **Python** is on the PATH used by the scheduled task, or edit the script to use a full path to `python.exe`.

Logs are written under `logs\` (gitignored).

## Database schema

Apply SQL in `schema/` via Supabase SQL editor in an agreed order, e.g.:

- `catapult_session_metrics.sql`
- `gymaware_summaries.sql`
- `athlete_identity.sql` (roster crosswalk; populate separately)

## GymAware allowlist

When `GYMAWARE_USE_ALLOWLIST=1` (or `python gymaware_export.py --allowlist`), only rows whose `athleteReference` appears in the workbook are written to JSON and (for upload) sent to Postgres. Use `--no-allowlist` for a full export regardless of `.env`.
