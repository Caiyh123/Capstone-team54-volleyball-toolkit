# Client integration requirements — Volleyball analytics toolkit

Collect the items below from the client (or their IT / performance staff) **before** each system can be connected in production. Store secrets in your password manager or `.env` — never in email or chat.

---

## 1. Catapult Connect (OpenField)

| Requirement | Notes |
|-------------|--------|
| **API token** | Generated in OpenField / Cloud: Settings → API Tokens (or equivalent). |
| **Regional base URL** | Must match where the account lives, e.g. `https://connect-au.catapultsports.com/api/v6` (AU), `connect-eu`, `connect-us`, `connect-cn`. Wrong region → failed calls. |
| **Confirmation** | Data is synced to OpenField Cloud (Connect only sees cloud-synced data). |

---

## 2. GymAware Cloud

| Requirement | Notes |
|-------------|--------|
| **Account ID** | **Required** — used as the **HTTP Basic username**. Found in GymAware Cloud: **Settings → Tokens** (API page). Not the same as a staff login. |
| **API token** | **Required** — used as the **HTTP Basic password**. Created under the same **Settings → Tokens** area; one token per application. |
| **Staff confirmation** | Only **Owners/Admins** can create API tokens. |

**Reference:** [GymAware Cloud API integration guide](https://gymaware.com/gymaware-cloud-api-integration-guide/)

---

## 3. WHOOP (Developer Platform)

| Requirement | Notes |
|-------------|--------|
| **Client ID** | From [WHOOP Developer Dashboard](https://developer-dashboard.whoop.com/) after creating an app. |
| **Client secret** | Same app; **server-side only**, never exposed to browsers. |
| **Redirect URI(s)** | Exact URL(s) registered in the dashboard; must match the integration’s OAuth callback. |
| **Requested scopes** | e.g. `read:recovery`, `read:cycles`, `read:workout`, `read:sleep`, `read:profile`, `read:body_measurement` — only what you need. |
| **`offline` scope** | Confirm if you need **refresh tokens** for long-lived access without re-consent. |
| **Per-athlete OAuth** | Plan for how each WHOOP user will **authorize** the app (WHOOP is per-member OAuth, not a single shared “team API key”). |

**Reference:** [WHOOP Getting Started](https://developer.whoop.com/docs/developing/getting-started), [OAuth 2.0](https://developer.whoop.com/docs/developing/oauth), [API](https://developer.whoop.com/api/)

---

## 4. VALD (Hub / external APIs)

| Requirement | Notes |
|-------------|--------|
| **Organization ID** | From **VALD Hub** — needed when requesting API access from VALD. |
| **API access approved** | Email **support@vald.com** requesting external API access; third-party integrations may require org approval + **API License Agreement**. |
| **Client ID** | Issued by VALD after approval (welcome email; credential link often **expires in 7 days** — retrieve promptly). |
| **Client secret** | Paired with Client ID; treat as confidential. |
| **Region** | Which **data region** the tenant uses (e.g. Australia East, US East, Europe West) — API base URLs are **region-specific**. |
| **Which products** | e.g. ForceDecks, NordBord, Dynamo, etc. — drives which Swagger docs and endpoints you implement. |

**Reference:** [How to integrate with VALD APIs](https://support.vald.com/hc/en-au/articles/23415335574553-How-to-integrate-with-VALD-APIs)

---

## 5. Teamworks AMS

| Requirement | Notes |
|-------------|--------|
| **API credentials for the AMS tenant** | Exact type depends on Teamworks provisioning (e.g. API key, OAuth client ID/secret, or other — **confirm with Teamworks / tenant admin**). |
| **Base URL / environment** | Production vs sandbox, if applicable. |
| **Tenant or org identifier** | If required by their API for scoping requests. |
| **Contact for API enablement** | Who at the club can approve API access or create keys. |

**Reference:** [Teamworks AMS API (Postman)](https://documenter.getpostman.com/view/31794560/2sA3rzJs2V), [Teamworks AMS](https://teamworks.com/ams/)

---

## 6. Infrastructure (your stack)

| Requirement | Notes |
|-------------|--------|
| **Supabase / Postgres `DATABASE_URL`** | Connection string for storing normalized metrics (if using current upload pipeline). |
| **Allowed IP / firewall** | If any vendor restricts by IP, collect egress IPs for your hosting environment. |

---

## 7. Optional: identity mapping

| Requirement | Notes |
|-------------|--------|
| **Athlete ID crosswalk** | How to match **Catapult athlete IDs**, **GymAware athlete references**, **VALD profile IDs**, **WHOOP user IDs**, and **Teamworks athlete IDs** (spreadsheet or master roster with stable internal ID). |

---

## Quick copy-paste checklist for the client

```
Catapult
[ ] API token
[ ] Regional Connect base URL confirmed

GymAware
[ ] Account ID (Settings → Tokens)
[ ] API token (Settings → Tokens)

WHOOP
[ ] Developer app: Client ID + Client Secret
[ ] Redirect URI(s) agreed and registered
[ ] Scopes + whether offline/refresh is needed
[ ] Plan for athlete OAuth consent

VALD
[ ] Organization ID (VALD Hub)
[ ] API access requested / approved with VALD
[ ] Client ID + Client Secret (from VALD)
[ ] Data region (AU / US / EU)

Teamworks AMS
[ ] API credentials (type per Teamworks)
[ ] Base URL / environment
[ ] Tenant details if required

General
[ ] DATABASE_URL (or agreed DB)
[ ] Athlete ID mapping policy across systems
```

---

*Internal template — adjust wording for client-facing PDF or email as needed.*
