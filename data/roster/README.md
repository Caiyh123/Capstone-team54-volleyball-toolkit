# Roster workbook (committed for online ETL)

This folder holds **`roster_new.xlsx`**, the team roster coaches can edit and the pipeline uses for filtering and identity mapping.

## For coaches (no `.env`, no API keys)

1. Get the file from the GitHub repo: **`data/roster/roster_new.xlsx`** (Download raw file, or clone the repo).
2. Edit in Excel: names, GymAware API ID, VALD profile ID, Catapult jersey/UUID, **WHOOP user ID** when available.
3. Return the updated file to the tech team:
   - **Option A:** Upload to your shared OneDrive/SharePoint and tell them to pull it in, or  
   - **Option B:** Open a GitHub pull request that only replaces `data/roster/roster_new.xlsx`, or  
   - **Option C:** Email the `.xlsx` attachment for someone to commit.

Coaches never need `DATABASE_URL`, tokens, or Python — only this spreadsheet.

## For ETL (GitHub Actions or local)

Scheduled ETL reads the committed path automatically:

| Environment | Setting |
|-------------|---------|
| **GitHub Actions** | `ROSTER_ALLOWLIST_XLSX=data/roster/roster_new.xlsx` (in `.github/workflows/daily_etl.yml`) |
| **Local / server** | Same path in `.env`, or omit `ROSTER_ALLOWLIST_XLSX` to use the committed file under `data/roster/` |

Each run of `python scheduled_etl.py --all` (or the Daily ETL workflow) **syncs the workbook into Supabase** first:

- `public.roster_cohort` — allowlist for `ROSTER_FILTER=1` and `*_roster` views  
- `public.athlete_identity` — Global Athlete ID (`VB-{GymAware ID}`) + vendor IDs including WHOOP  

Skip roster sync only if needed: `SCHEDULED_SKIP_ROSTER_SYNC=1`.

## Updating the roster in GitHub

```text
Edit data/roster/roster_new.xlsx  →  commit & push  →  next Daily ETL run applies changes
```

Confirm with your client that storing names and internal IDs in the repository is acceptable.

## Legacy filename

`allowlist.xlsx` was the old committed name. Use **`roster_new.xlsx`** going forward (includes WHOOP ID column). You may delete `allowlist.xlsx` after switching workflows to `roster_new.xlsx`.
