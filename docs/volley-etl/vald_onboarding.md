# VALD onboarding — read order (backend lead)

Use this sequence **before** credentials land so implementation matches current APIs and auth. **Do not skip the March 2026 breaking-changes article** — older examples may be wrong.

---

## Read order

### 1. API breaking changes (March 2026) — **read first**

Authentication and behaviour may have changed. Align any Python/R token code with this doc before copying older snippets.

- [API Updates – March 2026 Breaking Changes](https://support.vald.com/hc/en-au/articles/55205316766233-API-Updates-March-2026-Breaking-Changes)

### 2. VALD Hub (category)

Landing page for Hub docs; drill into **Build your own integrations**, Swagger links, and product-specific guides.

- [VALD Hub (support category)](https://support.vald.com/hc/en-au/categories/4416645858201-VALD-Hub)

*See also (access & token overview):* [How to integrate with VALD APIs](https://support.vald.com/hc/en-au/articles/23415335574553-How-to-integrate-with-VALD-APIs)

### 3. **valdr** R package (API exploration)

Useful for **prototyping pulls** (tenants, profiles, product APIs) until Python client exists in this repo.

- [A guide to using the valdr R package](https://support.vald.com/hc/en-au/articles/48730811824281-A-guide-to-using-the-valdr-R-package)

### 4. **valdrViz** R package (visualisation)

Optional for analysts; helps validate metrics before Power BI / warehouse marts.

- [A guide to using the valdrViz R package](https://support.vald.com/hc/en-au/articles/54002301348633-A-guide-to-using-the-valdrViz-R-package)

---

## After reading (backend checklist)

- [ ] Note **region** (AU / US / EU) and product Swagger URLs (Tenants, Profiles, ForceDecks, etc.).
- [ ] Implement **cached Bearer token** (client credentials); respect **429** and token expiry.
- [ ] Map **`tenantId`** / **`profileId`** to your **athlete mapping** table (same pattern as Catapult / GymAware).

---

## This repo (Volley)

- Config: `integrations/config.py` (`vald_settings()`), `.env.example`.
- Client: `integrations/vald/client.py` — OAuth client credentials + cached Bearer; `GET /tenants`, `GET /profiles`.
- Smoke / export: `python vald_export.py` (add `--profiles` to pull profiles per tenant).
- Schema: `schema/vald_profiles.sql` — staging for External Profiles; product metrics (ForceDecks, etc.) are separate follow-up tables.
- Load: after SQL is applied, `python upload_vald_profiles_to_supabase.py` (optional `--tenant-id <uuid>`).
- VA / ForceDecks **entity model** (definitions → tests → trials, keys, CMJ/DJ/IMTP hints): [vald_va_package_notes.md](./vald_va_package_notes.md).

---

*Suggested by SASI Data Analyst workflow: explore APIs with docs + R; Power BI against warehouse once marts exist.*
