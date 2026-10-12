# HighGround implementation specification — current synthesis

Derived from the preserved source `docs/spec/01-build-spec.md` and approved amendments in `docs/planning/approved-decisions.md`. This synthesis is the current implementation guide; the original handover remains unchanged. All Section 12 tasks are authorized for dependency-based parallel execution. Build and verify the complete Must journey locally first, then local Shoulds; host later. Individual Task N and calendar-start gates no longer apply. GitHub Issues tracks the work.

## Problem Statement

Flood-prone Malaysian shops need actionable information in the languages used by owners and workers: what stock to move, when to move vehicles, when to stop protecting property and leave, and how to document estimated losses afterward. A warning without shop context is insufficient. The demo focuses on Taman Sri Muda and must distinguish simulated events, stale observations, estimates and unreviewed translations.

## Solution

A Telegram bot collects a confirmed shop location, recipient languages, vehicle details and baseline video. Gemini produces an estimated inventory; deterministic rules select lift-first items. Valid official observations and contextual nearby photo reports lead to Watch, Warning or Danger. Warning explains prioritised stock and vehicle actions with sourced destination links. Danger always uses fixed language templates. Owners can confirm protective actions and later produce an estimated before/after loss report with upload-integrity evidence. The dashboard displays synthetic demo events, destinations and self-reported protection counters; hosted deployment remains deferred.

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
- Public dashboard exposes synthetic demo records only. Operator token protects simulation/reset; report links are unguessable bearer capabilities and media stays private. Alerts/BigQuery use hashed recipient identifiers; raw Telegram payloads are not retained for deduplication.
- No GitHub CI, Actions, Dependabot, other GitHub automation or repository-connected Cloud Build triggers. Local tests/build/deploy only. GitHub repository and Issues are authorized.
- Astra plans and coordinates each task, Sol implements, Astra inspects/corrects/rechecks, and Matt Standards/Spec review completes before task completion. Actual prerequisites govern progression; Shoulds remain gated on complete local Must acceptance (cloud acceptance deferred).

### Approved behaviour and priority resolutions

- Dashboard is part of Must acceptance. Dates are targets, not earliest starts; final code-freeze/submission deadlines remain unchanged. Hosting is deferred by the later local-first instruction.
- Vehicle action target is 15 minutes and stock 30 minutes after warning creation, strictly ordered and never described as predicted flood-arrival times. Danger bypasses property actions.
- Danger uses four fixed variants per language: destination/no destination × real/SIMULATION. The exact English wording, permitted destination placeholders, emergency footer and fixed translation-review notices are recorded in approved-decisions.md. Runtime cannot append generated advice or translate them.
- Watch uses short text until the Should offline card is implemented. Water-depth dots/memory map are Stretch and remain pitch-only; the other Must map layers are required.
- Every RM amount is an estimate. The integrity badge reads “File integrity verified”; hashes establish byte integrity, not recording authenticity. Confirmation value is exactly the immutable displayed item/action snapshot, preventing owner/worker retries from inflating totals.
- The source's Should policy-document deletion rule is the explicit retention exception: preserve the ledger/hash and deletion status, but never claim a deleted original currently passes byte comparison.
- Official observations require the approved configurable 90-minute freshness ceiling. Reject missing/future timestamps, device/error values and stale readings. Marine and geographically unattributed warnings are excluded. Expose source health and label simulations; no current claim of validated live official flood coverage.
- Workers self-start and explicitly consent through expiring single-use invitations; owners cannot enroll arbitrary chat IDs. Address candidates require confirmation. Risk components without sourced exposure or inventory data are unknown/uncredited, with a provisional explanation.
- Warning composition intentionally narrows free-form model prose: configured Gemini selects approved localized structure/situation keys under a strict schema; deterministic rendering supplies facts/actions and a fixed fallback. The user's five-minute decision default authorized this amendment, recorded with timing in approved-decisions.md. Danger still makes no model call.
- Use the published ADK FirestoreSessionService integration, verified against the local emulator, rather than a custom or in-memory production adapter. Model IDs remain configured; actual local app calls to Vertex use the dedicated approved project and explicit quota project.

### Remaining external limitations

- A fresh official flood feed and authoritative timezone attribution for naive source timestamps remain unavailable. Weather district mapping needs verified geography; no substring-based land inference from marine text.
- Historical destination designations and coordinates are sourced separately. Current opening status and parking floor restrictions remain unknown unless supported by an official current source; labels must preserve that uncertainty.
- Machine-generated translations are committed but remain `_reviewed:false` until native-speaker review. Fixed-template structure does not establish translation quality.
- Two consenting phone testers and real shop videos are still needed for the specified real-user acceptance. Synthetic fixtures and a real model schema/media probe can verify software paths but cannot establish valuation accuracy for a real shop.
- Local emulators verify application behaviour, not production IAM, GCS signed-URL enforcement, cloud resource provisioning or Cloud Run/Scheduler acceptance. These stay pending until hosting is authorized.
- The publicly inspected portal confirms track fit but currently supplies no additional accessible submission resources or authoritative deadline update; handover deadlines remain the planning reference.

Implementation-specific interfaces (item identity, progress/outbox records and recovery transactions) are designed and reviewed in each task brief. They are engineering decisions within the approved behaviour, not global user-approval blockers.

## Testing Decisions

Task 1 agreed seams: public GET /healthz contract and the actual blank dashboard build/run/browser view. No future services are mocked. Integration seams: exercise the bot/event boundary through persisted domain state and captured outbound Telegram effects, and the local report/dashboard HTTP boundary, repeated on hosted URLs when deployment is authorized. These are the highest useful seams for observable behaviour. Keep focused pure-rule tests for mandated triage, ranking, hashing and fixed templates; do not test implementation trivia. There was no application test suite at Task 1 start.

Required coverage: real API fixtures; null/stale/error observations and marine warning classification; location/radius selection; deterministic Danger in all eight languages including malformed model output and missing place; earlier vehicle deadline; rank/value arithmetic; immutable hash match/mismatch; duplicate updates and confirmations; restart recovery and partial-write retry; report privacy and deployed core M1/M3/M4/M5/M6. Compare normal, error and retry outcomes rather than only happy paths. Record measured neighbour-alert latency against the under-ten-second target; do not claim it without timing evidence.

All checks run locally. Cloud deployment acceptance is manual/scripted from the developer's machine. Matt review uses an agreed, resolvable fixed Git baseline and non-empty diff; separate Standards and Spec reviewers report independently, then Astra sends necessary corrections to Sol and rechecks. Task 1 review baseline is the committed task-start tree bb1b098.

## Out of Scope

Stretch implementation: flood memory map, drain watch, reopen checks, scam check, open-shops map, voice and live location. Also excluded: Vertex custom risk model, Earth Engine, WhatsApp, SMS delivery, insurer portal, web login and payments. Pitch-only statements must be labelled future work. All Section 12 tasks are authorized; Shoulds require complete local Must acceptance under the latest host-later instruction and Stretch remains pitch-only.

## Further Notes

The full feed inspected 13 October 2026 had 1,276 records, 725 null observation timestamps, and latest non-null timestamp 2024-02-23 14:45:00. Indicator counts: null 712, NORMAL 514, ERROR 45, ALERT 3, DANGER 2. Device status ON/OFF differs from severity; one inspected threshold set was non-monotonic. Weather returned four warnings; the inspected first concerned marine wind/seas and lacked district identifiers/coordinates. Detailed primary-source links and limitations are in the planning review.

The handover deadline and judging claims still need accessible official rules; the landing page supplied no readable rules in inspection. Plan remains four build days, code freeze Saturday 17 October at 14:00 MYT, and submission Sunday 18 October at 22:00 MYT, subject to verified portal rules.

Current execution and evidence live in internal-checklist.md, dependency-plan.md and the milestone verification notes. Remaining external limitations attach to their affected acceptance checks; they do not block unrelated implementation.
