# Roster allowlist (committed for CI)

This directory holds the **client roster workbook** used when `ROSTER_FILTER=1`.

- **Canonical file in repo:** `allowlist.xlsx` (copy of the client spreadsheet; sheet **GymAware** per `integrations/roster_allowlist.py`).
- **GitHub Actions** sets `ROSTER_ALLOWLIST_XLSX=data/roster/allowlist.xlsx` so scheduled ETL finds the file after checkout.

To update the roster: replace `allowlist.xlsx` with a new export from the client (keep the same filename) and commit.

Confirm with your client that storing this workbook in the repository is acceptable (it may contain names and internal IDs).
