# HighGround — Build Spec (for the AI coding assistant)

> **How to use this file:** paste this whole document into ChatGPT first with the line:
> *"This is the spec for my hackathon project. Read it fully. Don't write code yet — confirm you understand, list any questions, then wait for me to say 'Task 1'."*
> Then feed tasks from **Section 12** one at a time. After each task, run it, fix it, and commit before moving on.

---

## 1. Context

- **Hackathon:** Google Cloud AI Builder Cup 2026 (Hack2skill), track *Sustainability & Social Impact*.
- **Hackathon page (refer here for more details — rules, judging, submission format):** https://hack2skill.com/event/aibuildercup2026 · challenge list (login needed): https://hack2skill.com/event/aibuildercup2026/dashboard/challenges
- **Submission closes:** Mon 19 Oct 2026, 02:29 MYT. **Build window: 4 days, Tue 13 – Fri 16 Oct.** Code freeze Sat 17, 14:00. Submit by Sun 18 Oct, 22:00 MYT.
- **Hard rules:** fresh code written during the hackathon · must use **Gemini and/or ADK (Agent Development Kit)** · must be deployed on **Cloud Run or Firebase**.
- **Deliverables:** deployed link · **public** GitHub repo · demo video under 3 minutes · PDF pitch deck.
- **Judging:** GenAI & Technical **40%** · Impact 25% · Innovation 25% · UX 10%.
  → Priority: a visibly *agentic* Gemini/ADK system that works end to end, over polish.
- **Team:** Lucas (only developer, full-stack) + Zhao Wei (interviews, deck, video, data collection).

## 2. Product in one line

**HighGround is an AI flood copilot for small shops. Other apps tell you a flood is coming. HighGround tells you what to lift, where to park, keeps working when the network goes down — then proves what you lost.**

### Problem (for README and deck)
- Floods are ~85% of Malaysia's disasters. The Dec 2021 floods cost RM6.1B; about two-thirds (~RM4B) was uninsured. **Vehicles alone were RM1.0B** — double the losses on business premises.
- Only ~15% of SMEs (AIG Malaysia, 2019) had flood cover.
- Official warnings are river-level sirens (~2 km range, BM only) and apps people must check themselves. Nobody tells a shop owner *what to do, now*, and nobody helps them prove what they lost.
- ~342 telco towers in Selangor were knocked out in Dec 2021 (flooding + power cuts) — online alerts fail exactly when needed.
- In Nov 2022 Shah Alam council opened a multi-storey car park for residents' cars during a flood alert — announced only in a Facebook post.
- Household aid is already digital (RM1,000 via MyIBJKM). **Small businesses have no equivalent** — that is our gap.

### Differentiators (vs Etiqa flood alerts, BencanaBanjir, MyPublicInfoBanjir)
1. **Shop-to-shop alerts by radius**, pushed to Telegram (not a map you have to open).
2. **"Lift these first"** — a value-ranked list of what to save, from the shop's own video, plus a live "RM protected" counter.
3. **Vehicle rescue** — where to park, with a route, before the water comes.
4. **Blackout-proof** — an offline flood card saved to the phone at the first sign of risk.
5. **Tamper-evident video evidence → loss report** for small businesses (no competitor found).
6. **Eight languages**, including those of foreign workers who run many shops day to day.
7. **Flood memory map** — street-level water depth built from shops' water-line photos.
8. **Whole flood lifecycle, not just the warning:** prevent (insurance check, blocked drains) → warn → protect → recover (waste sorting, safe reopening, "we're open" map) → trust (scam check, self-improving alerts).

## 3. Users and the demo moments

User: owner (or worker) at a shop-lot business (mini-market, workshop, eatery, phone shop) in a flood-prone area (demo location: **Taman Sri Muda, Shah Alam**).

The demo video is built around these moments — every task should serve one of them:

| # | Moment | What the judge sees |
|---|---|---|
| M1 | **Onboard in Telegram** | `/start` → pick language (8) → share location → shop name/type → send a 30–45 s walk-through video → bot replies with an itemised inventory, a "Verified evidence" note, and the shop's **lift-first list** |
| M2 | **Watch → offline card** | Rain/early warning → bot sends a **saved-to-phone flood card image**: lift-first list, where to park, nearest evacuation centre, mini map, emergency numbers |
| M3 | **Official warning** | Dashboard "Simulate JPS warning" → agent finds shops within radius → each gets a tailored alert: "Lift these 8 items first (≈RM6,200). Move your van to Pasar Moden Sri Muda car park, level 2+, by 18:30" + route links → owner taps **Done** → dashboard "RM protected" counter rises |
| M4 | **Neighbour report** | Shop A sends a photo of water rising → agent verifies it with Gemini → Shops B–E within 500 m alerted within seconds; dashboard map shows the ripple |
| M5 | **Danger level** | Escalation → message is ONLY the fixed "Leave now" template + nearest safe point (hard-coded safety rule) |
| M6 | **After the flood** | Owner sends a damage video + a water-line photo → loss report page (before vs after, RM, timestamps, evidence hashes) → "Download PDF"; water depth appears on the **flood memory map** |
| M7 | **Where do I go? (anyone)** | Any Telegram user sends `/check` + a location → nearby warnings, level, nearest safe point, safe parking and shops open after a flood |
| M8 | **Before the monsoon** | Owner sends a photo/PDF of their insurance policy → "Flood is NOT covered" or "Underinsured by ~RM28,000 vs your inventory"; owner reports a blocked drain → council-ready complaint + hotspot on map |
| M9 | **Recovery** | Loss report also sorts every item: throw away / salvage / recycle / bulky pickup → dashboard shows waste volume per street for the council; safe-to-reopen checklist; shop taps "We're open" |
| M10 | **It learns** | After each alert: "Did water reach your shop?" → dashboard shows alert accuracy improving and the radius tuned per street |

## 4. Scope

**Build:** everything in Section 3, live dashboard (map + feed + counters), report page, polling of the real data.gov.my feeds, demo mode.

**Do NOT build (roadmap in deck):** Vertex AI custom risk model, Earth Engine flood-extent layers, WhatsApp, SMS fallback, insurer portal, web login, payments.

**Priorities (cut from the bottom if behind):**
- **Must:** core (M1, M3, M4, M5, M6 report) + S1 vehicle rescue, S2 lift-first, S4 evidence, S6 languages.
- **Should:** S3 offline card, L4 `/check`, R1 insurance check, R2 waste sorting, R3 learning loop.
- **Stretch:** S5 flood memory map, R4 drain watch, R5 safe-to-reopen, R6 scam check, R7 "we're open" map, R8 voice, L6 live location.
- **Rule:** never start a Should item until all Musts work end to end on the deployed URL; never start Stretch until Shoulds are done. Anything not built goes on the deck's "full lifecycle" slide.

Simple rule-based risk score is fine (Section 9).

## 5. Architecture

```
Telegram users ──webhook──▶ Cloud Run: api (Python, FastAPI + ADK agents)
                                 │  ├─ ADK agents (Section 6) ──▶ Gemini on Vertex AI
                                 │  ├─ Firestore (shops, events, alerts, inventories, reports, safe_points, water_marks)
                                 │  ├─ Cloud Storage (videos, photos, generated flood cards)
                                 │  ├─ Pub/Sub topic: flood-events  (publish on every new event)
                                 │  └─ BigQuery dataset: highground (event log, alert log, evidence ledger)
Cloud Scheduler (every 5 min) ──▶ POST /jobs/poll-warnings ──▶ data.gov.my APIs
Cloud Run: web (Next.js) ──▶ reads api JSON endpoints ──▶ dashboard map, report pages
```

**Stack decisions (fixed — don't change without asking):**
- Backend: **Python 3.12, FastAPI, Google ADK (`google-adk`), `google-genai` SDK (Vertex AI mode)**, `python-telegram-bot` or raw Bot API via `httpx`, **Pillow** for rendering the offline card image.
- Frontend: **Next.js (App Router) + Tailwind + Leaflet (OpenStreetMap tiles)**. Polls `/api/events` every 3 s (no websockets).
- Storage: Firestore (Native mode), private Cloud Storage bucket `highground-media-<project>`.
- Gemini model names are **config variables** (`GEMINI_FAST_MODEL`, `GEMINI_PRO_MODEL`): current Flash for messages/photos/translations, current Pro for video inventory and comparison.
- Region: `asia-southeast1` for Cloud Run, Firestore, bucket (Vertex AI: a region where the chosen Gemini models are available).
- Pub/Sub: publish every flood event; alert dispatch can run in-process for MVP (subscriber optional). Pub/Sub must still be visibly used.
- BigQuery: one row per event, per alert, per "Done" confirmation and per media upload (evidence ledger). Feeds the stats bar and the deck.

## 6. ADK agent design (the core of the GenAI score)

One **root agent `highground_coordinator`** with three sub-agents. Deterministic safety, geo and hashing logic live in **tools (Python functions)**, not in the LLM.

### 6.1 `triage_agent`
- Input: an official warning OR a shop's photo report.
- Tools: `verify_flood_photo(gcs_uri)`, `get_official_warnings()`, `get_recent_reports(lat, lng, radius_m, minutes)`.
- Output (structured): `{event_type, level: "watch"|"warning"|"danger", lat, lng, radius_m, confidence, reason}`.
- Rules: MET heavy-rain warning for the district, or a single unverified shop report → `watch` (shops within 300 m for reports). Verified photo (confidence ≥ 0.7) OR ≥2 reports within 500 m in 30 min OR an official JPS warning → `warning`. Official "danger"/"bahaya" status OR verified photo with water inside premises → `danger`.

### 6.2 `alert_agent`
- Input: triage output.
- Tools: `find_shops_in_radius`, `get_shop_profile`, `get_lift_first_list(shop_id)`, `find_nearest_safe_point(lat, lng, type)`, `render_offline_card(shop_id, event_id)`, `send_telegram(chat_id, text, buttons, photo?)`, `log_alert(...)`.
- Per level:
  - **watch** → send the **offline flood card** (S3) + short text "Save this image now in case the network goes down."
  - **warning** → Gemini-written message in the shop's language: situation, distance, **lift-first list (top items + RM at risk)** (S2), **where to park + route** (S1), **one deadline**, nearest evacuation centre + route, buttons: **"✅ Done — stock lifted"**, **"✅ Vehicle moved"**, "Quick 30-second video update (optional)".
  - **danger** → **hard rule in the `send_telegram` wrapper**: ignore LLM text, send fixed `LEAVE_NOW[lang]` with only the safe point name/link filled in; no buttons except the route; never a video request.
- "Done" buttons → record `protected_value_rm` (sum of lift-first items at floor/low height) and vehicle saved → BigQuery + dashboard counter.

### 6.3 `loss_agent`
- Tools: `build_inventory(video_gcs_uri)`, `rank_lift_first(inventory_id)`, `compare_inventories(before_id, after_video_gcs_uri)`, `estimate_water_mark(photo_gcs_uri)`, `create_report(shop_id, comparison)`.
- Produces the inventory + lift-first list after onboarding (and monthly refresh), the loss report and water-mark depth after a flood.

### 6.4 Root agent
- Routes: Telegram message type + context → correct sub-agent. Scheduler poll → triage → alert.
- ADK session state keyed by Telegram `chat_id` for onboarding and the after-flood conversation.

## 6b. Location features

| ID | Feature | How | Priority |
|---|---|---|---|
| L1 | **Shop location** | Telegram "Share location" button. Fallback: typed address → geocode (Google Maps Geocoding API or Nominatim) → bot sends the pin back as a venue: "Is this your shop?" | Must |
| L2 | **Report location** | Photo report defaults to the shop's location; bot asks "Is this at your shop?" — if not, ask for a location share | Must |
| L3 | **Nearest safe point + route** | `find_nearest_safe_point(lat, lng, type)` over `safe_points` (haversine). Alerts include the nearest evacuation centre and nearest safe parking, each with `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}` | Must |
| L4 | **`/check` for anyone** | No signup: `/check` + location → active warnings/reports within 2 km, level, nearest safe point + safe parking, one-line Gemini summary | Should |
| L5 | **Dashboard geo layers** | Safe points (green), safe parking (blue P), radius circles, shaded danger zones, water-depth dots | Must |
| L6 | **Live location during Danger** | Optional Telegram live location; dashboard shows a count only | Stretch |

**Safe points data:** no national open dataset of evacuation centres (PPS) for Selangor exists. Seed `safe_points` for the demo area from Zhao Wei's list (council / NADMA announcements; multi-storey car parks such as Pasar Moden Sri Muda, opened by MBSA for residents' cars in Nov 2022). Each has `source` and `verified`. UI labels: "Listed evacuation centre", "Council-designated parking", or "Higher ground (unverified)". Never claim a place is open unless an official source says so — alerts say "previously designated by MBSA; check it's open".

## 6c. Stand-out features

### S1 — Vehicle rescue (Must)
- `safe_points.type` adds `"parking"` (multi-storey car parks, elevated lots), with `min_level` (e.g. 2).
- Shops with `has_vehicle=true` get "Move your {vehicle_type} to {name}, level {min_level}+, by {HH:MM}" + route, and a **"✅ Vehicle moved"** button.
- Deadline = earlier than the stock deadline (cars need to leave before roads flood).
- Dashboard counter: **vehicles moved**.

### S2 — "Lift these first" + RM protected (Must)
- `rank_lift_first`: from the latest inventory, take items with `height` "floor" or "low", sort by `qty × est_unit_value_rm` ÷ effort (Gemini estimates `lift_effort` 1–3: 1 = one person, seconds; 3 = heavy/needs two people). Return top 8 with RM at risk.
- Shown in onboarding reply ("If water comes, lift these first"), in Warning alerts and on the offline card.
- **"✅ Done — stock lifted"** → `protected_value_rm` = sum of those items → BigQuery row → dashboard counter **"RM protected tonight"**.

### S3 — Blackout-proof offline card (Should)
- At `watch` level (and on demand via `/card`), `render_offline_card` generates a **1080×1920 PNG** with Pillow: shop name, lift-first list with RM, where to park + address, nearest evacuation centre + address, a static mini map (OpenStreetMap static tile or a simple drawn map with pins), emergency numbers (999, Bomba 994), timestamp, all in the shop's language. Text content written by Gemini (Flash) as JSON, layout done in code.
- Sent as a Telegram photo with "Save this image — it works without signal."
- Roadmap (deck only): SMS fallback when Telegram is unreachable.

### S4 — Tamper-evident evidence (Must)
- On every media upload (baseline video, update video, after video, flood photo, water-line photo): compute **SHA-256** of the original bytes, record `uploaded_at` (server time), Telegram `message.date`, sender `chat_id` hash, and location (shop or shared) → write to `media/{id}` in Firestore **and** append a row to BigQuery table `evidence_ledger` (append-only).
- The report page shows each item's evidence: file hash (short), time, location, and a **"Verified evidence"** badge when the stored file's hash still matches the ledger.
- Never edit uploaded originals; derived files are stored separately.

### S5 — Flood memory map (Stretch)
- After a flood (in the after-flood conversation), bot asks for a photo of the **water line on a wall/door**. `estimate_water_mark` (Flash) returns `est_depth_cm`, `reference_object` (door, shelf, wall socket…), `confidence`.
- Saved to `water_marks` with location; dashboard layer shows depth dots coloured by depth; `/check` mentions "Water reached ~80 cm here in the last flood".
- Pitch: street-level depth data that insurers and councils don't have.

### S6 — Eight languages (Must)
- Languages: `ms` Bahasa Malaysia, `en` English, `zh` 中文, `ta` Tamil, `bn` Bengali, `ne` Nepali, `my` Burmese, `id` Bahasa Indonesia.
- Static bot strings and **LEAVE_NOW templates**: write `en.json`, then generate the other 7 once with Gemini into `i18n/*.json`, commit them, and mark `"_reviewed": false` until a native speaker checks (Zhao Wei will try). Never translate LEAVE_NOW at runtime.
- Dynamic alerts: Gemini writes directly in the target language.
- A shop can register a **second recipient** (e.g. a worker) with their own language; both get alerts.

## 6d. Lifecycle features (R1–R8)

### R1 — "Am I actually covered?" insurance check (Should)
- `/policy` → owner sends photos or a PDF of their business insurance policy / schedule → `ingest_media` → `read_policy` (Pro) extracts: insurer, policy type, `flood_covered` (yes / no / unclear — look for "flood", "special perils", "banjir"), `sum_insured_rm` for stock/contents, excess, expiry date.
- Compare `sum_insured_rm` with the latest inventory `total_est_value_rm` → reply: covered / not covered / underinsured by ≈RM X, plus "Ask your agent about the flood (special perils) add-on before the monsoon". Never give legal or financial advice; always say "check with your insurer".
- Policy documents are sensitive: store only extracted fields + the hash; delete the original file after extraction unless the owner taps "Keep a copy".
- Dashboard (aggregate only): % of registered shops without flood cover, total uninsured stock RM.

### R2 — Flood waste sorting & salvage (Should)
- Extend `compare_inventories` output: each damaged/destroyed item gets `disposition`: "discard_contaminated" (food, drinks, medicine, cosmetics, anything absorbent that touched floodwater), "salvage_clean" (sealed metal/plastic/glass goods that can be cleaned), "recycle" (metal, e-waste: phones, appliances, electronics), "bulky_pickup" (furniture, fridges, shelving), plus `est_volume_m3` and `est_weight_kg`.
- Report page: a "What to do with each item" section; salvageable items can be flagged "available to donate".
- Dashboard layer: estimated waste volume per street (sum of reports) + estimated lorry loads (assume a configurable `LORRY_CAPACITY_M3`, default 10) → for the council's clean-up planning.
- Food-safety line is fixed text: "Throw away food, drinks and medicine that touched floodwater."

### R3 — Learning loop (Should)
- 6 hours after each warning/danger alert (or when the event closes), bot asks: "Did water reach your shop?" buttons: No / Street only / Entrance / Inside (+ optional depth).
- Store as `alerts.outcome`; compute per-area precision (alerts where water came ÷ alerts sent) in BigQuery.
- `area_calibration/{geohash6}`: adjust `radius_multiplier` (0.5–1.5) and `min_level_to_alert` per area with a simple rule: precision < 0.3 over ≥5 alerts → shrink radius 10%; missed floods (outcome "inside" with no alert) → grow radius 10%. The triage agent reads calibration before deciding.
- Dashboard: "Alert accuracy" stat + trend; feed line "Radius for Sri Muda Sek. 25 tuned to 850 m after 6 reports".
- Demo: seed historical outcomes so the trend is visible.

### R4 — Drain watch (Stretch)
- `/drain` + photo + location → `classify_drain` (Flash): `blockage` none/partial/severe, `cause` (rubbish, silt, plants, construction), confidence → `drain_reports`; dashboard hotspot layer; bot returns a ready-to-send complaint text for the council (location, photo link, date, severity) for the owner to submit through the council's official channel. We do NOT submit on their behalf.

### R5 — Safe to reopen (Stretch)
- After a flood, a fixed checklist (static i18n text, not generated): don't switch on power if water reached sockets or the DB box — get a registered electrician to check; wear boots and gloves when cleaning; throw away contaminated food; see a doctor and mention flood exposure if you get a fever within 2 weeks (leptospirosis risk).
- Optional: owner sends a photo of the DB box / sockets → `check_electrical_photo` (Flash) only says whether a water line appears near them and repeats "get it checked" — never says "safe".

### R6 — Scam check (Stretch)
- `/scam` + forwarded message, poster image or link → `check_aid_message` (Flash): red flags (asks for bank login/OTP, payment to apply, unofficial links, urgency), does it name a real agency, and the official channel to verify (from a static `official_channels.json`: NADMA, JKM, MBSA, state government, BSN). Output always "likely fake / can't verify — check {official channel}". Never says "genuine".

### R7 — "We're open" map (Stretch)
- After a flood, shops tap "We're open" + tick what they have (food, drinking water, medicine, hardware, phone charging) → `shops.open_status` with expiry 48 h → dashboard layer + `/check` lists open shops nearby.

### R8 — Voice (Stretch)
- Owner can reply with a Telegram voice note at any step → Gemini (audio input) transcribes + extracts intent. Alerts can be sent as a voice note too (Cloud Text-to-Speech) for owners who choose "Voice" in settings. LEAVE_NOW voice files are pre-generated and checked, never generated at runtime.

## 7. External data

- **Flood warnings:** `GET https://api.data.gov.my/flood-warning` (realtime, JPS). **Fetch it first and inspect the real JSON**, then write the parser. Save a captured response to `api/fixtures/flood_warning_sample.json`.
- **Weather warnings:** `GET https://api.data.gov.my/weather/warning` (MET Malaysia). Same approach; fixture `weather_warning_sample.json`. Heavy-rain warnings for the shop's district → `watch`.
- Dedupe by station/warning ID + status; only new or escalated items create events.
- **Demo mode** (`DEMO_MODE=true`): `/demo/simulate-warning` injects a fake watch/warning/danger at a chosen lat-lng (default: Sungai Klang near Taman Sri Muda, Shah Alam).

## 8. Data model (Firestore)

```
shops/{shop_id}
  shop_name, shop_type, owner_name?, lat, lng, address_text, floor: "ground"|"upper",
  has_vehicle: bool, vehicle_type?: "car"|"van"|"lorry"|"motorcycle",
  recipients: [{telegram_chat_id, language, role: "owner"|"worker"}],
  risk_score: 0-100, baseline_inventory_id, lift_first: [{item_name, qty, value_rm, lift_effort}],
  lift_first_value_rm, created_at, is_demo: bool

inventories/{inventory_id}
  shop_id, kind: "baseline"|"update"|"after", media_id, created_at,
  items: [{name, category, qty, est_unit_value_rm, location_in_shop,
           height: "floor"|"low"|"high", lift_effort: 1|2|3, timestamp_s}],
  total_est_value_rm

media/{media_id}
  shop_id?, kind: "baseline_video"|"update_video"|"after_video"|"flood_photo"|"waterline_photo",
  gcs_uri, sha256, bytes, uploaded_at, telegram_date, sender_hash, lat, lng

events/{event_id}
  source: "jps"|"met"|"shop_report"|"demo", level, lat, lng, radius_m,
  confidence, reason, media_id?, reporter_shop_id?, raw?, created_at

alerts/{alert_id}
  event_id, shop_id, telegram_chat_id_hash, level, language, text, card_media_id?,
  sent_at, delivered: bool, distance_m,
  stock_done_at?, protected_value_rm?, vehicle_done_at?

reports/{report_id}
  shop_id, before_inventory_id, after_inventory_id, created_at,
  lost_items: [{name, qty, est_value_rm, evidence_timestamp_s, condition: "destroyed"|"damaged"|"missing"}],
  total_loss_rm, summary_text, confidence_note, evidence_media_ids: [...]

safe_points/{id}
  name, type: "pps"|"parking"|"high_ground", min_level?, lat, lng, address_text,
  source, verified: bool, is_demo: bool

water_marks/{id}
  shop_id?, media_id, lat, lng, est_depth_cm, reference_object, confidence, flood_date, created_at

policies/{id}                       # R1 — extracted fields only
  shop_id, insurer, policy_type, flood_covered: "yes"|"no"|"unclear", sum_insured_rm?,
  excess_rm?, expiry_date?, media_sha256, original_deleted: bool, created_at

alerts.outcome?: "none"|"street"|"entrance"|"inside", outcome_depth_cm?, outcome_at?     # R3
area_calibration/{geohash6}: radius_multiplier, min_level_to_alert, precision, n_alerts, updated_at

reports.lost_items[].disposition, est_volume_m3, est_weight_kg, donate: bool              # R2

drain_reports/{id}: media_id, lat, lng, blockage, cause, confidence, created_at          # R4
shops.open_status?: {open: bool, has: ["food","water","medicine","hardware","charging"], until}   # R7
shops.prefers_voice?: bool                                                                # R8
```

BigQuery tables: `events`, `alerts`, `confirmations`, `evidence_ledger` (append-only), `outcomes`.

## 9. Risk score (rule-based MVP)

`risk_score = 40*(ground floor) + 20*(within 500 m of a river polyline OR past event OR water mark) + 20*(lift_first_value_rm > RM2,000) + 20*(has_vehicle)` → capped at 100. Shown in onboarding reply and dashboard. Roadmap: Vertex AI model.

## 10. API endpoints (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| POST | `/telegram/webhook` | All Telegram updates (secret token header check) |
| POST | `/jobs/poll-warnings` | Cloud Scheduler (OIDC auth) |
| POST | `/demo/simulate-warning` | `{lat, lng, level}` (DEMO_MODE only) |
| POST | `/demo/reset` | Clear demo events/alerts/confirmations, keep seeded shops |
| GET | `/api/shops` | Shops for the map (no chat IDs / phone numbers) |
| GET | `/api/events?since=` | Event + alert + confirmation feed |
| GET | `/api/reports/{id}` | Loss report JSON incl. evidence |
| GET | `/api/media/{id}/verify` | Recompute hash of stored file, compare with ledger |
| GET | `/api/safe-points` | Safe points + parking |
| GET | `/api/water-marks` | Water-depth layer |
| GET | `/api/stats` | Shops, alerts sent, avg alert latency, **RM protected**, **vehicles moved** |
| GET | `/api/waste` | Waste volume per street (R2) |
| GET | `/api/drains` | Drain hotspots (R4) |
| GET | `/api/open-shops` | Shops open after a flood (R7) |
| POST | `/jobs/ask-outcomes` | Scheduler: send "Did water reach your shop?" follow-ups (R3) |
| GET | `/healthz` | Health check |

## 11. Gemini prompts (starting points — always use a JSON response schema)

**verify_flood_photo** (Flash, image)
> You are verifying a flood report from a shop in Malaysia. Return JSON: `is_flooding` (bool), `water_location` ("street"|"entrance"|"inside_premises"|"none"), `est_depth_cm` (int or null), `confidence` (0–1), `reason` (≤20 words). If unrelated, a screenshot, or clearly old/staged, set `is_flooding=false`.

**build_inventory** (Pro, video)
> Walk-through video of a small shop in Malaysia. List visible stock and equipment, grouping identical items. For each: `name`, `category`, `qty`, `est_unit_value_rm` (typical Malaysian replacement price), `location_in_shop`, `height` ("floor" ≤30 cm, "low" ≤1 m, "high" >1 m), `lift_effort` (1 = one person in seconds, 2 = one person with effort, 3 = heavy/two people/not movable), `timestamp_s`. Only what is visible.

**rank_lift_first** — pure Python on the inventory (no LLM): filter floor/low, score = value ÷ lift_effort, top 8.

**compose_alert** (Flash)
> Write a Telegram alert in {language} for {shop_name}. Situation: {reason}, {distance_m} m away, level {level}. Include: (1) "Lift these first" with up to 5 items from {lift_first} and total ≈RM{value}; (2) if vehicle: move {vehicle_type} to {parking_name} level {min_level}+ by {vehicle_deadline}; (3) stock deadline {stock_deadline}. Max 90 words, plain and calm, one ⚠️ at the start. Do not invent places or numbers.

**offline_card_text** (Flash) → JSON `{title, lift_lines[], parking_line, shelter_line, emergency_line, footer}` in {language}; layout rendered by Pillow.

**compare_inventories** (Pro, after-video + baseline JSON)
> Baseline inventory (JSON) and a post-flood video. For each baseline item: `condition` ("ok"|"damaged"|"destroyed"|"missing"), `evidence_timestamp_s`, lost value. Don't invent items. Return `lost_items`, `total_loss_rm`, `summary_text` (3 sentences), `confidence_note`.

**estimate_water_mark** (Flash, image)
> Photo of a water line/stain left by a flood on a wall, door or shelf. Estimate the water height above floor level. Return `est_depth_cm`, `reference_object` used for scale, `confidence`, `reason`. If no clear water line, return null depth.

**read_policy** (Pro, images/PDF)
> Malaysian business insurance policy or schedule. Extract `insurer`, `policy_type`, `flood_covered` ("yes" only if flood / special perils / banjir is explicitly included for this policy; "no" if explicitly excluded or absent from a fire policy's listed perils; otherwise "unclear"), `sum_insured_rm` for stock/contents, `excess_rm`, `expiry_date`, `evidence_quote` (the exact line you relied on). Do not guess numbers.

**classify_drain** (Flash, image) → `blockage`, `cause`, `confidence`, `reason`.

**check_aid_message** (Flash, text/image) → `red_flags[]`, `claimed_agency`, `verdict`: "likely_fake"|"cannot_verify", `official_channel_to_check` (choose from the provided list only).

**check_electrical_photo** (Flash, image) → `water_line_near_sockets_or_db`: yes/no/unclear, `reason`. Never output "safe".

**translate_i18n** (Flash, one-off script) — translate `en.json` values into {language}, keep keys and placeholders `{like_this}` unchanged.

**LEAVE_NOW templates** (static, in i18n files, never generated at runtime). EN: "⚠️ DANGER: Flooding is reaching your area. Leave now and move to higher ground. Do not stop to record video or move stock. Nearest safe point: {safe_point_name} {route_link}. Call 999 if you are trapped."

## 12. Build tasks — 4-day build (feed one at a time)

Each task: write the code, give the exact commands to run, and say how to verify. Small typed modules. Don't move on until I confirm.

**Shape of the 4 days:** Days 1–3 build every **Must** and deploy by the end of Day 3. Day 4 = dashboard, demo data, hardening, then **Should** items only if time allows. **Stretch items are pitch-only** (deck slide) unless everything else is done. Sat 17 = record video + deck (code freeze 14:00 Sat, bug fixes only). Sun 18 = submit, no new code.

### Day 1 — Tue 13 Oct: foundations + onboarding
- **Task 1 — Repo + scaffolding.** Monorepo `api/`, `web/`, `infra/`, README, `.env.example`, MIT licence. *Done when:* `/healthz` works locally and `npm run dev` shows a blank dashboard.
- **Task 2 — GCP setup script.** `infra/setup.sh`: enable APIs (Run, Firestore, Storage, Pub/Sub, BigQuery, Scheduler, Vertex AI, Secret Manager), bucket, Firestore, topic `flood-events`, BigQuery dataset + tables (`events`, `alerts`, `confirmations`, `evidence_ledger`, `outcomes`), service account (least privilege), secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`.
- **Task 3 — data.gov.my clients.** Both endpoints, fixtures, parsers to a common `Warning` model, dedupe, tests.
- **Task 4 — Telegram webhook.** Secret check, `/start`, `infra/set_webhook.sh`, local tunnel.
- **Task 5 — i18n + onboarding (M1 minus video, S6).** `en.json` + one-off `translate_i18n` script → 8 language files (incl. LEAVE_NOW). Onboarding: language → location (or address → geocode → confirm) → shop name/type → ground floor? → vehicle? (type) → optional second recipient (worker, own language) → save shop, reply with risk score.

### Day 2 — Wed 14 Oct: the agent + alerts
- **Task 6 — ADK skeleton.** Coordinator + triage / alert / loss sub-agents with stub tools; local script runs a fake warning end to end and prints decisions.
- **Task 7 — Alert dispatch (M3).** `find_shops_in_radius`, `compose_alert`, `send_telegram` wrapper with the **danger hard rule**, `log_alert` (Firestore + BigQuery), Pub/Sub publish, `/demo/simulate-warning`.
- **Task 8 — Safe points + vehicle rescue (L3, S1).** `safe_points` (pps / parking / high_ground) + seed script, `find_nearest_safe_point(type)`, parking + shelter lines with route links, **"Vehicle moved"** button → confirmation row.
- **Task 9 — Evidence ledger + neighbour reports (S4, M4).** Shared `ingest_media()` for ALL uploads (Telegram download → SHA-256 → GCS → `media` doc → `evidence_ledger`). Photo → `verify_flood_photo` → triage rules → alert neighbours (exclude reporter). Rate-limit 1 report/shop/10 min.
- **Task 10 — Danger escalation + polling (M5).** Escalation path; tests that danger messages contain only template + safe point. `/jobs/poll-warnings` (OIDC) + `infra/scheduler.sh` (5-minute job).

### Day 3 — Thu 15 Oct: video, reports, first deploy
- **Task 11 — Baseline inventory + lift-first (M1, S2).** Video (≤20 MB, ask for 30–45 s) → `ingest_media` → `build_inventory` → `rank_lift_first` → reply: top items, total RM, lift-first list, "Verified evidence". Warning alerts include lift-first; **"Done — stock lifted"** → `protected_value_rm` → BigQuery.
- **Task 12 — After-flood report (M6).** "Flood is over" button / `/report` → after-video → `compare_inventories` → report doc → summary + link.
- **Task 13 — Report page.** `/report/[id]`: before vs after table, total loss, evidence panel (hash, time, location, verified badge via `/api/media/{id}/verify`), disclaimer, print CSS → Save as PDF.
- **Task 14 — First deploy.** Dockerfiles, `infra/deploy.sh` (api + web to Cloud Run), webhook → Cloud Run URL, Scheduler → prod. *Done when:* M1, M3, M4, M5, M6 work from my phone on the deployed URLs. **Deploying today is mandatory — don't leave it to Day 4.**

### Day 4 — Fri 16 Oct: dashboard, demo, hardening, then Shoulds
- **Task 15 — Dashboard.** Leaflet map on Taman Sri Muda: shop pins by alert level, safe points + parking icons, radius circles, danger zones; live feed with the triage `reason`; stats bar (**RM protected**, **vehicles moved**, alerts sent, avg alert time; add **alert accuracy** / **% shops without flood cover** only if R3 / R1 are built); demo buttons (Watch / Warning / Danger / Reset).
- **Task 16 — Seed demo data + redeploy.** 6 demo shops (2 real test Telegram accounts, 4 virtual) with baseline inventories, lift-first lists, vehicles for 3, real safe points from Zhao Wei's list.
- **Task 17 — Hardening.** Retries/fallbacks on every Gemini call (timeout or bad JSON → retry once → friendly apology), logging, secrets out of repo, README (architecture diagram, setup, screenshots, "Built with").
- **Should items — only after Tasks 1–17 work on the deployed URL. In this order, each ~1–3 h, redeploy after each:**
  - **18 — Offline card (S3, M2):** `offline_card_text` + Pillow renderer (Noto Sans fonts for all 8 scripts), sent at `watch` and via `/card`.
  - **19 — Insurance check (R1, M8):** `/policy`, `read_policy`, compare with inventory value, delete-original rule.
  - **20 — Waste sorting (R2, M9):** `disposition`, volume, weight in the comparison; report section; `/api/waste` + map layer.
  - **21 — `/check` (L4, M7).**
  - **22 — Learning loop (R3, M10):** outcome buttons, `outcomes`, `area_calibration`, seeded history, accuracy stat.

### Sat 17 Oct — record (code freeze 14:00)
- Morning: finish any Should item already started; otherwise bug fixes only.
- 14:00 freeze → reset demo data → record the demo video with Zhao Wei → final README screenshots.

### Sun 18 Oct — submit
- No new code. Final checks: deployed link works in an incognito window, repo is public, video < 3:00, deck PDF. **Submit by 22:00 MYT.**

### Stretch (pitch-only unless everything above is done)
S5 flood memory map · R4 drain watch · R5 safe to reopen · R6 scam check · R7 "we're open" map · R8 voice · L6 live location. These go on the deck's "full flood lifecycle" slide marked "next".

## 13. Non-functional rules

- **Safety first:** Danger = fixed template + safe point only. Never ask for video at Danger. Vehicle deadline always earlier than stock deadline. Every alert ends with "Call 999 in an emergency" in the user's language.
- **No advice we can't stand behind:** insurance check says "check with your insurer"; scam check never says "genuine"; electrical check never says "safe"; health lines are fixed text.
- **Places:** never say a shelter or car park is open unless an official source says so; label unverified points.
- **Privacy:** minimal data; owner name optional; dashboard never shows chat IDs or phone numbers (store hashed chat IDs in alerts/BigQuery); private bucket; unguessable report IDs.
- **Honesty in UI:** all RM values labelled "estimate"; photo verification and water depth show confidence; machine-translated languages flagged until reviewed.
- **Evidence integrity:** originals immutable; ledger append-only.
- **Latency target:** report → neighbour alerts in under 10 s.
- **No CI in GitHub — strict:** do NOT create `.github/workflows/`, GitHub Actions, Dependabot, or any other GitHub-hosted automation. All tests, linting, builds and deploys run **locally** via scripts (`infra/test.sh`, `infra/deploy.sh`, `gcloud` commands). Don't use Cloud Build triggers connected to the repo either; `gcloud run deploy --source` from my machine is fine.
- **Code:** type hints, small modules, `.env.example`, no secrets in git, `pytest` for parsers, triage rules, danger rule, lift-first ranking and hashing.

## 14. Repo layout

```
highground/
  api/
    main.py
    agents/            # coordinator.py, triage.py, alert.py, loss.py
    tools/             # geo.py, telegram.py, gemini.py, datagov.py, storage.py, bq.py,
                       # media.py (ingest + sha256), card.py (Pillow), lift_first.py
    models.py
    i18n/              # en ms zh ta bn ne my id .json
    fonts/             # Noto Sans families for the offline card
    fixtures/
    tests/
    Dockerfile
  web/
    app/page.tsx                 # dashboard
    app/report/[id]/page.tsx
    Dockerfile
  infra/  setup.sh  test.sh  deploy.sh  set_webhook.sh  scheduler.sh  seed_demo.py  translate_i18n.py
  README.md  LICENSE  .env.example
```

## 15. Environment variables

`GCP_PROJECT`, `GCP_REGION=asia-southeast1`, `VERTEX_LOCATION`, `GEMINI_FAST_MODEL`, `GEMINI_PRO_MODEL`, `GCS_BUCKET`, `PUBSUB_TOPIC=flood-events`, `BQ_DATASET=highground`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `WEB_BASE_URL`, `API_BASE_URL`, `DEMO_MODE`, `DEFAULT_ALERT_RADIUS_M=1000`, `NEIGHBOUR_RADIUS_M=500`, `CHECK_RADIUS_M=2000`, `GOOGLE_MAPS_API_KEY` (geocoding only; optional with Nominatim), `HASH_SALT` (for hashing chat IDs), `LORRY_CAPACITY_M3=10`, `OUTCOME_ASK_AFTER_H=6`.
