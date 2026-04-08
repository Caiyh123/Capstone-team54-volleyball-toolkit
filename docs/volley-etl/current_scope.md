# Current integration scope



**Product direction:** **Scheduled** export→upload (users don’t manually trigger routine refreshes) plus **RCA storytelling** in BI/dashboard — not live streaming. See **[product_direction.md](./product_direction.md)**.



**Active now**



| Source | Use | Scripts / code |

|--------|-----|----------------|

| **Catapult Connect** | Session load / stats, activity lists, jump events (via API) | `handshake.py`, `get_activities.py`, `get_session_data.py`, `bulk_export.py`, `upload_to_supabase.py`, `Jump Data - BEACH VB.R` |

| **GymAware Cloud** | Strength / VBT summaries, jump-related metrics (`height`, power, velocity on sets) | `integrations/gymaware/client.py`, `gymaware_export.py` (JSON export), `verify_integrations.py` |

| **Load index** | `sum(total_player_load) / jump_count` (Catapult stats + jump events, same logic as `Jump Data - BEACH VB.R`) | `load_index.py` → `load_index_result.json` |



**Deferred (credentials or deliverable pending)**



- **WHOOP** — **via Teamworks AMS** when API exposes wearable fields; fallback: direct [WHOOP Developer API](https://developer.whoop.com/) if AMS cannot supply data — see **[whoop_via_teamworks.md](./whoop_via_teamworks.md)**

- **VALD** (Hub API — client id/secret + region after approval)

- **Teamworks AMS** — tenant API + **daily wellness 1–10** (soreness, mental/physical wellbeing)

- **Francois** — spike tracking script (narrative layer alongside jump load)



**Frontend**



- Dashboard: [volleyball-data-analysis-toolkit.vercel.app](https://volleyball-data-analysis-toolkit.vercel.app/) — OAuth callback `/auth/callback`



**Database**



- Primary store: Supabase/Postgres — evolve toward **mart / views** for Power BI or Tableau (see product_direction.md)


