# Open questions

Track decisions here; assign an owner and target date when possible.

## Product and access

- [ ] **Final list of data sources** for the capstone deliverable (Catapult + GymAware only vs WHOOP/VALD in scope).
- [ ] **Athlete roster / ID crosswalk**: who provides SASI or internal IDs vs GymAware/Catapult IDs, and when will the spreadsheet be maintained?
- [ ] **WHOOP**: direct Developer API vs Teamworks AMS — which path is approved first?
- [ ] **VALD**: API access status, region, and which products (ForceDecks, NordBord, etc.).

## Ethics and compliance

- [ ] **Research ethics / institutional approval** for use of identifiable performance data (if applicable).
- [ ] **Consent** model for wearable and cloud vendor data (athletes, staff).

## Infrastructure

- [ ] **Hosting** for any OAuth bridge (e.g. Render) and agreed **redirect URIs** registered with vendors.
- [ ] **Supabase** project ownership, backups, and who has **service role** access.
- [ ] **Power BI**: workspace, refresh schedule after ETL, gateway if needed.

## Operations

- [ ] **Machine** running scheduled sync (staff PC vs server) and **Python path** for Task Scheduler.
- [ ] **GymAware allowlist workbook**: canonical filename, location on the sync machine, and whether `GYMAWARE_USE_ALLOWLIST=1` is required in production.

## Frontend (if used)

- [ ] Relationship between **Vercel app** OAuth callbacks and **server-side** WHOOP redirect URIs (must match vendor registration exactly).
