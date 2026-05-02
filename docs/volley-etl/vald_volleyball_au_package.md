# VALD — Volleyball AU client package alignment

The reference materials under `Package_Volleyball_AU_UniA` (Volleyball Australia / Uni workflow) define how **ForceDecks** data is modeled for reporting: **tests**, **trials** (with `resultId` → metric definition), and **metric definitions**. That package uses the R **`valdr`** CRAN client against VALD’s **External ForceDecks** regional host.

## Where the package lives

On disk (sibling to this repo in many workspaces):

`D:\CursorProjects\Volley\Package_Volleyball_AU_UniA`

| Package area | Contents |
|--------------|----------|
| `README.md` | PATH A: R → Excel → Power BI; PATH B: PBIP project |
| `data/README.md` | Keys: `resultId`, `profileId`, `testId`, `trialId`; Excel samples for definitions / profiles / tests / trials |
| `r_proj/README.md` | `valdr` flows: `get_forcedecks_tests_only`, `get_forcedecks_trials_only`, definitions, ForceFrame vs ForceDecks |
| `pbi/` | Semantic model tables (e.g. `dev_VALD_GetAllTests`) — **redacted** in the packaged PBIP |

## How this toolkit maps to that model

| VA package artifact | VALD API (conceptual) | Supabase target (this repo) |
|---------------------|------------------------|------------------------------|
| VA_VALD_Metric_Definitions | GET `/resultdefinitions` | `vald_forcedecks_result_definitions_staging` (optional; set `VALD_FORCEDECKS_SYNC_DEFINITIONS=1`) |
| VA_VALD_Profile_ID | External **Profiles** API (existing ETL) | `vald_profiles` |
| VA_VALD_Tests | External ForceDecks **GET `/tests`** (`TenantId`, `ModifiedFromUtc`, optional `ProfileId`) | `vald_forcedecks_tests_staging` |
| VA_VALD_Trials | Team-scoped **GET** `.../v2019q3/teams/{teamId}/tests/detailed/{dateFrom}/{dateTo}` (embedded `trials[]`) | `vald_forcedecks_trials_staging` (requires `VALD_FORCEDECKS_TEAM_ID`) |

**ForceFrame** (`VALD_API_BASE_FORCEFRAME`, GET `/tests/v2`) is a **different VALD product surface** than **ForceDecks** (`VALD_API_BASE_FORCEDECKS`). Your tenant may license one or both. The VA Excel/Power BI path is **ForceDecks–centric**; use `upload_vald_forcedecks_to_supabase.py` for parity with that package.

## Operational notes

- **Incremental window:** R README stresses **`modifiedDateUtc`** for updates, not only `testDate`. The GET `/tests` call uses **`ModifiedFromUtc`** accordingly (`SCHEDULED_VALD_FORCEDECKS_LOOKBACK_DAYS`).
- **Team ID for trials:** The OpenAPI still exposes trial detail via **team** + date range. Set **`VALD_FORCEDECKS_TEAM_ID`** from VALD Hub / your tenant so the detailed endpoint can run; without it, the script still loads **tests** only (same grain as filtering tests in the package).
- **Swagger:** Australia East ForceDecks docs are published under the extforcedecks host (e.g. `.../swagger/index.html` → `v2019q3/swagger.json`).

## Scripts (toolkit root)

- `python upload_vald_forcedecks_to_supabase.py`
- Orchestrated after profiles (and optionally ForceFrame) via `scheduled_etl.py` unless `VALD_SKIP_FORCEDECKS=1`.

See also: [vald_va_package_notes.md](./vald_va_package_notes.md), [vald_onboarding.md](./vald_onboarding.md).
