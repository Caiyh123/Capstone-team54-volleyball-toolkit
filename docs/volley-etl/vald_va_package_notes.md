# VALD — Volleyball Australia reference model (external package)

This repo does **not** include third-party R/Power BI projects. The notes below distill **usable structure** from a packaged VA / Uni workflow (ForceDecks + Power BI) for aligning future **Python + Supabase** work with the same domain concepts.

## Entities and keys (ForceDecks-oriented)

| Concept | Typical key | Role |
|--------|----------------|------|
| Metric / result definition | `resultId` | Describes a measured metric (name, unit, category). |
| Profile (athlete) | `profileId` | Links to `public.vald_profiles` and `athlete_identity.vald_profile_id`. |
| Test (session) | `testId` | One ForceDecks test event; ties to `profileId`, dates, test type. |
| Trial (rep) | `trialId` | Repetition within a test; carries `resultId` / definition and measured values. |

**Trial column map (typical):** `testId`, `trialId`, `resultId` (definition), `profileId` (as athlete / hub id in exports).

Use the **region-specific ForceDecks Swagger** (e.g. Australia East host under [Build your own integrations](https://support.vald.com/hc/en-au/sections/5213949442585-Build-your-own-integrations)) for exact JSON shapes before defining DDL.

## Reporting hints (test types)

A VA Power BI template prioritised **test types** such as **CMJ**, **DJ**, **IMTP** when filtering ForceDecks data. Treat as **product requirements**, not API constraints—confirm available `testType` values in Swagger for your tenant.

## Implementation in *this* repo

- **Done:** OAuth client credentials, Tenants + Profiles API, `vald_profiles`, `upload_vald_profiles_to_supabase.py`.
- **Not done:** ForceDecks tests/trials/definitions ingestion—add `VALD_API_BASE_FORCEDECKS` (or per-product env) in `integrations/config.py`, extend `ValdClient` or a dedicated module, and new `schema/*.sql` once field names are frozen from Swagger.

## Related

- [vald_onboarding.md](./vald_onboarding.md) — official VALD read order and links.
- [client_integration_requirements.md](./client_integration_requirements.md) — VALD checklist.
