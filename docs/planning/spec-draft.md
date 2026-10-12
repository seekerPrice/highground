# HighGround implementation specification — DRAFT

Derived from docs/spec/01-build-spec.md, the exact complete handover copy and source of truth, plus current user instructions. This draft is reviewable, not an approved replacement. The user authorized GitHub spec/ticket publication; unresolved decisions attach to affected tasks and do not block unrelated Task 1 scaffolding. Requirements below retain Section 12 numbering. Approved Q1–Q3 amendments are recorded in docs/planning/approved-decisions.md; remaining items marked PROPOSED require resolution before affected implementation. Task 1 is explicitly authorized. GitHub Issues is the selected tracker; explicit Task N gates remain.

## Problem Statement

Flood-prone Malaysian shops need actionable information in the languages used by owners and workers: what stock to move, when to move vehicles, when to stop protecting property and leave, and how to document estimated losses afterward. A warning without shop context is insufficient. The demo focuses on Taman Sri Muda and must distinguish simulated events, stale observations, estimates and unreviewed translations.

## Solution

A Telegram bot collects a confirmed shop location, recipient languages, vehicle details and baseline video. Gemini produces an estimated inventory; deterministic rules select lift-first items. Valid official observations and contextual nearby photo reports lead to Watch, Warning or Danger. Warning explains prioritised stock and vehicle actions with sourced destination links. Danger always uses fixed language templates. Owners can confirm protective actions and later produce an estimated before/after loss report with upload-integrity evidence. A deployed dashboard displays events, destinations and self-reported protection counters.

The real-source polling capability must expose source health honestly. The inspected flood feed is stale; the product cannot currently claim validated live official flood warnings. The demonstration may use clearly labelled simulated events, under approved Q2. Fresh official flood input remains unresolved.

## User Stories

1. As a shop owner, I want onboarding in one of eight languages so that I understand the bot.
2. As an owner, I want to share or confirm my shop location so that nearby alerts target the correct place.
3. As an owner, I want to record shop type, floor and vehicle details so that instructions reflect my circumstances.
4. As an owner, I want a worker to opt in with their own language so that both of us can act.
5. As an owner, I want a short baseline video converted into visible inventory estimates so that I need not enter every item.
6. As an owner, I want a lift-first list so that I can prioritise valuable low stock.
7. As an owner, I want Watch notifications to identify early concern without overstating certainty.
8. As an owner, I want a Warning to state the situation, estimated stock exposure, action targets and destinations so that I can prioritise action.
9. As a vehicle owner, I want an earlier vehicle action target than the stock target so that the two actions have a clear order.
10. As an owner, I want sourced destination labels and opening-status qualifications so that I do not mistake an old designation for current availability.
11. As a recipient, I want Danger to use fixed leave-now guidance so that generated content cannot distract me with stock or video requests.
12. As a recipient without a known destination, I want a fixed fallback so that missing place data does not block urgent guidance.
13. As an owner, I want to confirm actions once so that protection counters do not double count repeated or worker taps.
14. As a nearby shop, I want relevant neighbour reports to reach me quickly so that local observations are useful.
15. As a reporter, I want to confirm where a photo was taken so that it does not silently use the wrong shop location.
16. As a recipient, I want old or unrelated observations excluded from current alerts so that stale data does not produce false warnings.
17. As an owner, I want uploaded bytes, hash, receipt time and attributed location recorded so that later integrity checks are transparent.
18. As an owner after a flood, I want to compare damage footage with my baseline so that I can prepare an estimated loss report.
19. As a report reader, I want estimates, confidence and evidence limitations clearly stated so that I understand what has and has not been established.
20. As an owner, I want a printable report so that I can save a PDF.
21. As a dashboard viewer, I want locations, event radii, danger zones and a live feed so that I can follow the demo.
22. As a dashboard viewer, I want estimated protection, vehicles moved and alert metrics so that impact is visible without exposing recipient identifiers.
23. As a demonstrator, I want labelled synthetic events and a demo-only reset so that the presentation is repeatable without modifying real shop records.
24. As an operator, I want restart recovery, deduplication and bounded retries so that failures do not silently lose work or inflate metrics.
25. As an owner, I want a saved multilingual flood card (Should) so that selected guidance remains readable offline.
26. As an owner, I want cautious policy extraction and default document deletion (Should) so that I can discuss possible coverage gaps with my insurer.
27. As an owner and cleanup planner, I want estimated disposal categories and volumes (Should) so that cleanup planning has a starting point.
28. As any Telegram user, I want a location-based check without shop signup (Should) so that I can view relevant warnings and listed destinations.
29. As an owner, I want to report what flooding occurred (Should) so that measured outcomes can inform constrained calibration.
30. As an operator, I want model names and credentials configured outside source so that deployment can adapt without publishing secrets.

## Implementation Decisions

### Settled constraints

- Python 3.12, FastAPI, Google ADK and google-genai in Vertex mode; Telegram through the permitted client or raw Bot API; Pillow for the Should card.
- Next.js App Router, Tailwind, Leaflet and OpenStreetMap tiles; three-second polling, no websockets.
- Firestore Native, private Cloud Storage, Pub/Sub event publishing, BigQuery logs/ledger, Cloud Scheduler and Cloud Run. Primary region asia-southeast1; Vertex location must support configured models.
- One coordinator with triage, alert and loss sub-agents. Geo, ranking, hashing and safety boundaries are deterministic tools.
- Eight languages; static strings and Danger templates generated once, committed and marked unreviewed until checked. Never translate Danger at runtime.
- Every upload uses shared ingestion and records hash, receipt time, Telegram time, sender hash and attributed location. Downloaded Telegram bytes may already differ from camera originals.
- Models return schema-validated data. Inventory values, damage and outcomes remain estimates rather than proved facts.
- Pub/Sub is visibly used. BigQuery records events, alerts, confirmations and evidence; duplicate retries must not inflate counters.
- Public dashboard excludes recipient identifiers; bucket is private and report identifiers unguessable. Detailed access policy remains unresolved.
- No GitHub CI, Actions, Dependabot, other GitHub automation or repository-connected Cloud Build triggers. Local tests/build/deploy only. GitHub repository and Issues are authorized.
- Astra plans and coordinates each task, Sol implements, Astra inspects/corrects/rechecks, and Matt Standards/Spec review completes before task completion. User confirmation gates each next task.

### Approved amendments and remaining proposals

- APPROVED Q1: Task 15 follows Task 14 and is included in the Must deployment target. Dates are targets, so earlier progress is allowed; Shoulds still require deployed acceptance of Tasks 1–17. Individual Task N gates and final deadlines remain.
- APPROVED Q3: Two deterministic action targets, vehicle strictly before stock, never predicted flood-arrival times. Configuration is settled when that task is implemented.
- APPROVED Q3: Reconcile the emergency footer inside fixed Danger templates and use a fixed no-destination variant. Exact wording/placeholders/translations are checked before use; no generated additions.
- APPROVED Q3: Destination wording must not guarantee safety. The source template currently says “Nearest safe point”; exact replacement wording is established before use, not silently rewritten here.
- PROPOSED: Watch uses short text until the Should offline card is deployed.
- PROPOSED: Water-depth dots and the memory map remain pitch-only despite their mention in Must L5; other Must dashboard layers ship.
- PROPOSED: Clarify the specified “Verified evidence” badge as file-integrity verification only; proposed replacement label is “File integrity verified.”
- PROPOSED: Align the displayed/accessible items, inventory snapshot and confirmation value so that top-five/top-eight prompt differences cannot overcount protection.
- PROPOSED: Explicitly exempt policy originals from immutable retention when the Should deletion rule applies; the hash/ledger remains, but deleted originals cannot pass a current byte comparison.
- APPROVED Q2: Reject stale readings, expose source unavailability and use clearly labelled simulations in the demo. This does not prove live official flood warnings work; a fresh official source is unresolved.

### Unresolved interfaces and records

Agree before the relevant task: source event identity/lifecycle/freshness; district mapping; stable item identities and action snapshots; recipient opt-in; processing status and resumable writes; public/demo/report access; destination source date/opening state; missing river-risk inputs. These decisions must fit the fixed stack. Do not invent a river dataset, an ADK Firestore adapter or freshness guarantees.

## Testing Decisions

Task 1 agreed seams: public GET /healthz contract and the actual blank dashboard build/run/browser view. No future services are mocked. Future-task proposed seams: exercise the bot/event boundary through persisted domain state and captured outbound Telegram effects, and the deployed report/dashboard HTTP boundary. These are the highest useful seams for observable behaviour. Keep focused pure-rule tests for mandated triage, ranking, hashing and fixed templates; do not test implementation trivia. There was no application test suite at Task 1 start.

Required coverage: real API fixtures; null/stale/error observations and marine warning classification; location/radius selection; deterministic Danger in all eight languages including malformed model output and missing place; earlier vehicle deadline; rank/value arithmetic; immutable hash match/mismatch; duplicate updates and confirmations; restart recovery and partial-write retry; report privacy and deployed core M1/M3/M4/M5/M6. Compare normal, error and retry outcomes rather than only happy paths. Record measured neighbour-alert latency against the under-ten-second target; do not claim it without timing evidence.

All checks run locally. Cloud deployment acceptance is manual/scripted from the developer's machine. Matt review uses an agreed, resolvable fixed Git baseline and non-empty diff; separate Standards and Spec reviewers report independently, then Astra sends necessary corrections to Sol and rechecks. Task 1 review baseline is the committed task-start tree bb1b098.

## Out of Scope

Stretch implementation: flood memory map, drain watch, reopen checks, scam check, open-shops map, voice and live location. Also excluded: Vertex custom risk model, Earth Engine, WhatsApp, SMS delivery, insurer portal, web login and payments. Pitch-only statements must be labelled future work. Task 1 implementation is explicitly authorized; no later task is authorized.

## Further Notes

The full feed inspected 13 October 2026 had 1,276 records, 725 null observation timestamps, and latest non-null timestamp 2024-02-23 14:45:00. Indicator counts: null 712, NORMAL 514, ERROR 45, ALERT 3, DANGER 2. Device status ON/OFF differs from severity; one inspected threshold set was non-monotonic. Weather returned four warnings; the inspected first concerned marine wind/seas and lacked district identifiers/coordinates. Detailed primary-source links and limitations are in the planning review.

The handover deadline and judging claims still need accessible official rules; the landing page supplied no readable rules in inspection. Plan remains four build days, code freeze Saturday 17 October at 14:00 MYT, and submission Sunday 18 October at 22:00 MYT, subject to verified portal rules.

Next task-level decisions: exact Danger/no-destination translations, freshness/geometry handling, target configuration and public exposure. Q1–Q3 principles are already accepted. Infrastructure account facts should be inspected where possible rather than put to the user as unnecessary questions. No source/spec contradiction is silently resolved by this draft.
