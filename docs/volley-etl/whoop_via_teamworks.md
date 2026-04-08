# WHOOP data via Teamworks AMS

**Direction:** Ingest **WHOOP-derived metrics through Teamworks AMS** APIs (or exports), not the standalone [WHOOP Developer API](https://developer.whoop.com/) — unless AMS cannot supply what you need and ethics/contracts allow a direct integration.

---

## Why this path

- **Single credential set** and **one vendor DPA/ethics thread** with the sporting organisation where possible.
- AMS often **normalises** wearable data next to **subjective wellness** (your 1–10 soreness / wellbeing), which supports **RCA overlays** in Power BI.

---

## What you need from Teamworks / client (before coding)

1. **Confirmation** that WHOOP (or “recovery / strain / sleep” from wearables) is **actually landed in AMS** for your cohort — not only visible in the UI with no API access.
2. **API access** for your tenant: base URL, auth type (OAuth client, API key, etc.) — see [Teamworks AMS API (Postman)](https://documenter.getpostman.com/view/31794560/2sA3rzJs2V).
3. **Object model:** which **resources** or **forms** hold WHOOP-related fields (names change by tenant configuration).
4. **Grain:** e.g. **per athlete per calendar day** vs per session — must match your `mart_athlete_day` plan.
5. **Field list:** exact **JSON keys** or column names for sleep, recovery, strain, HRV, etc. (whatever AMS exposes).

---

## Implementation pattern (Volley repo)

When credentials exist:

1. Add **`integrations/teamworks/`** client (auth + HTTP helpers).
2. Add **`teamworks_export_whoop_slice.py`** (or a generic **`teamworks_export.py`** with query params) that pulls the agreed resources for a **date range** and writes JSON.
3. Add **Supabase table** e.g. `teamworks_whoop_daily` or a wider `teamworks_wellness_daily` if sleep/recovery sit in the same form as subjective metrics.
4. Join to **`athlete_external_ids`** using the **AMS athlete id** (or email) from the client master map.

**Env (placeholder until known):** `TEAMWORKS_AMS_BASE_URL`, `TEAMWORKS_AMS_TOKEN` (or OAuth vars) — see `.env.example`.

---

## Risk / fallback

If AMS **does not** expose WHOOP fields over the API, options are:

- **Manual / scheduled export** from AMS UI (if allowed), or  
- **Direct WHOOP OAuth** (separate app registration + member consent) — revisit ethics and James’s AMS questions.

---

## Links

- [Teamworks AMS API — Postman public docs](https://documenter.getpostman.com/view/31794560/2sA3rzJs2V)
- [Teamworks AMS product](https://teamworks.com/ams/) (context)

---

*Update this doc with real endpoint paths and sample JSON once the tenant Postman collection is walked through with IT.*
