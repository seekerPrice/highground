# Section 12 ticket plan — published mapping source

The user now authorizes implementation of all tasks, parallel by true dependencies without calendar or individual Task N waits. Published in seekerPrice/highground: parent specification #1, Task 1–22 as issues #2–23. The latest separate user instruction supplies implementation authorization. The handover source is docs/spec/01-build-spec.md. Attach unresolved notes only to affected tasks; unrelated later questions do not block Task 1. This grouped plan supplied the issue bodies; unresolved proposed changes still require agreement.

The artificial sequential chain is superseded. dependency-plan.md contains the current technical blockers; the original per-ticket references below are updated to that graph. Every task includes Astra coordination, Sol corrections, relevant local tests and Matt Standards/Spec review against the agreed baseline.

APPROVED current execution: build by the technical DAG, verify Musts fully locally, then implement Shoulds locally. Hosting is deferred; cloud acceptance remains pending. Dates allow earlier progress and Task numbers are traceability labels. Stretch features are pitch-only. Do not silently substitute a synthetic feed for a live official feed.


## 01 — Repo + scaffolding

**Blocked by:** No implementation-task blockers; user explicitly authorized Task 1. Future-task decisions do not block scaffolding.

**What it delivers:** Local API health and blank dashboard run from a documented monorepo.

**Acceptance:** API health returns success; frontend opens locally; example environment contains no secrets; no prohibited automation.

**Status:** Implementation and local acceptance complete; Astra correction loop and both Matt review axes passed. Tasks 2 and 3 dispatched under all-task authorization.

## 02 — GCP setup script

**Blocked by:** Task 1.

**What it delivers:** Repeatable setup provisions the fixed Google Cloud services and secret references.

**Acceptance:** APIs, regional resources, tables and least-privilege identities exist; rerun is safe; credentials stay out of source.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 03 — data.gov.my clients

**Blocked by:** Task 1.

**What it delivers:** Actual responses become validated, deduplicated warning observations with freshness and source status.

**Acceptance:** Captured fixtures cover actual schemas, stale/null/error records and marine weather; old DANGER never alerts; device ON/OFF is not severity.

**Proposed issue label:** needs-info — Agree stale-source fallback, freshness threshold and weather geography/type mapping before this behaviour is accepted.

## 04 — Telegram webhook

**Blocked by:** Task 1.

**What it delivers:** A real Telegram user reaches the authenticated bot entry point.

**Acceptance:** Correct secret accepted and wrong secret rejected; duplicate updates do not duplicate work; local tunnel setup is documented.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 05 — i18n + onboarding

**Blocked by:** Task 2, Task 4.

**What it delivers:** Owner selects one of eight languages, confirms location and shop/vehicle details, optionally links a worker.

**Acceptance:** Shop persists across restart; address fallback confirms a pin; recipient opts in; eight static templates preserve placeholders; review status is honest; risk unknowns are not invented.

**Proposed issue label:** needs-info — Confirm static Danger wording/placeholder rules, risk unknowns and recipient-linking flow.

## 06 — ADK skeleton

**Blocked by:** Task 1.

**What it delivers:** Coordinator routes a fake warning through the specified sub-agents with inspectable decisions.

**Acceptance:** Local fake warning completes; contracts are typed/validated; state persistence approach is explicit; no future feature is represented as implemented.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 07 — Alert dispatch

**Blocked by:** Task 2, Task 3, Task 5, Task 6.

**What it delivers:** A simulated event reaches eligible recipients and appears in event/alert records.

**Acceptance:** Radius selection works; recipients receive their language; Pub/Sub is visibly used; BigQuery records sends; Danger bypasses generated text; demo access policy is applied.

**Proposed issue label:** needs-info — Danger/fallback and two-target policy accepted; settle exact fixed strings, target configuration and public demo access.

## 08 — Safe points + vehicle rescue

**Blocked by:** Task 7.

**What it delivers:** Alerts include sourced parking/evacuation destinations and record vehicle confirmations.

**Acceptance:** No invented places/opening claims; destination missing fallback works; vehicle action deadline precedes stock; repeated/worker taps cannot count one vehicle twice.

**Proposed issue label:** needs-info — Confirm destination fallback and deadline policy; sourced place data required.

## 09 — Evidence ledger + neighbour reports

**Blocked by:** Task 2, Task 5, Task 6, Task 7.

**What it delivers:** Uploaded photos preserve downloaded bytes, record hashes and produce validated nearby alerts.

**Acceptance:** All media uses shared ingestion; partial-write retries are recoverable; unrelated photos rejected; reporter excluded; per-shop limit enforced; ledger append protected.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 10 — Danger escalation + polling

**Blocked by:** Task 3, Task 7, Task 8, Task 9.

**What it delivers:** Scheduled real-source polling and escalating events use deterministic safety handling.

**Acceptance:** Scheduler OIDC enforced; stale observations excluded; escalation deduplicated; all language Danger paths emit only approved fixed content and route button.

**Proposed issue label:** needs-info — Implement approved fixed footer/fallback and stale exclusion; exact strings/freshness configuration require task-level decision.

## 11 — Baseline inventory + lift-first

**Blocked by:** Task 5, Task 6, Task 7, Task 9.

**What it delivers:** Video becomes an estimated inventory and ranked lift-first list that warning confirmations reference.

**Acceptance:** Hosted download size handled at 20 MB; visible items only; floor/low rank deterministic; estimate labels present; counted items match immutable action snapshot; duplicate confirmation is harmless.

**Proposed issue label:** needs-info — Resolve displayed items versus confirmation snapshot/value.

## 12 — After-flood report

**Blocked by:** Task 11.

**What it delivers:** Owner requests recovery reporting, uploads an after-video and receives an estimated loss report link.

**Acceptance:** Baseline association persists; comparison does not invent items; report confidence/limitations shown; failure/retry does not create duplicate reports.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 13 — Report page

**Blocked by:** Task 12.

**What it delivers:** An unguessable report link shows before/after estimates, evidence and a printable report.

**Acceptance:** Evidence verification recomputes stored-byte hash against ledger; mismatch is visible; no authenticity guarantee; private media exposure follows policy; print-to-PDF is usable.

**Proposed issue label:** needs-info — Resolve integrity-badge wording and report/media access policy.

## 14 — First deploy

**Blocked by:** Task 2, Task 10, Task 11, Task 12, Task 13.

**What it delivers:** API and web run on Cloud Run and the phone completes core Must moments.

**Local acceptance:** Packaging/local containers and documented manual deployment path verified without hosted automation. **Deferred hosting acceptance:** M1/M3/M4/M5/M6 on deployed URLs, production webhook/Scheduler and secrets verified when hosting is authorized.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 15 — Dashboard

**Blocked by:** Task 7, Task 8, Task 9, Task 11.

**What it delivers:** Map, event feed, protection counters and demo controls show the Must journey.

**Acceptance:** Shop levels, sourced places, parking, event radii and danger zones render; polling updates every three seconds; counters do not duplicate; no private recipient data; unavailable Stretch layers omitted.

**Proposed issue label:** needs-info — Thursday deployment target/order accepted; exact Must layers exclude pitch-only Stretch depth dots.

## 16 — Seed demo data + redeploy

**Blocked by:** Task 14, Task 15.

**What it delivers:** Six demo shops make the deployed story reproducible.

**Acceptance:** Two real test accounts and four virtual shops; three vehicles; sourced destinations; reset affects only demo records; synthetic data labelled and redeploy verified.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 17 — Hardening

**Blocked by:** Task 16.

**What it delivers:** Deployed Must journey survives expected failures and has usable operational documentation.

**Acceptance:** Gemini timeout/bad schema retries once then explains failure; restart/idempotency verified; logs omit secrets; architecture/setup/screenshots recorded; all Must behaviour rechecked locally; cloud-only acceptance explicitly pending.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 18 — Offline card

**Blocked by:** Task 17. Complete local Must acceptance required before local Should implementation; cloud acceptance pending.

**What it delivers:** At Watch or on request, owner receives a multilingual image that can be saved offline.

**Acceptance:** 1080×1920 image renders all scripts; facts/destinations constrained; time/emergency text present; saved-file limitation explained; local watch and command tested; deployment deferred.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 19 — Insurance check

**Blocked by:** Task 17 and full local Must acceptance before Should implementation; cloud acceptance pending. Independent Should work may then run in parallel.

**What it delivers:** Owner uploads a policy and receives cautious extracted coverage and estimated shortfall information.

**Acceptance:** Evidence-backed extraction; unclear remains unclear; insurer-check reminder fixed; original deleted by default and retention opt-in respected; aggregate dashboard only.

**Proposed issue label:** needs-info — Confirm policy deletion exception to immutable-original retention.

## 20 — Waste sorting

**Blocked by:** Task 17 and full local Must acceptance before Should implementation; cloud acceptance pending. Independent Should work may then run in parallel.

**What it delivers:** Loss report provides item disposal categories and aggregate estimated cleanup volumes.

**Acceptance:** Fixed food-safety wording; dispositions/estimates validated; volumes and configurable lorry capacity aggregate consistently; report/map updated and verified locally; deployment deferred.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 21 — /check

**Blocked by:** Task 17 and full local Must acceptance before Should implementation; cloud acceptance pending. Independent Should work may then run in parallel.

**What it delivers:** Any user shares a location to view current nearby warnings and listed destinations.

**Acceptance:** No shop signup needed; two-kilometre search and freshness work; no invented opening/safety claims; absent Stretch open-shops feature omitted.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.

## 22 — Learning loop

**Blocked by:** Task 17 and full local Must acceptance before Should implementation; cloud acceptance pending. Independent Should work may then run in parallel.

**What it delivers:** Owner feedback produces transparent outcome metrics and constrained area calibration.

**Acceptance:** Scheduled outcome prompt works; denominators and nonresponses explicit; multiplier bounds enforced; minimum sample checked; no suppression of authoritative Danger; seeded history labelled; verified locally with hosting deferred.

**Proposed issue label:** ready-for-agent — subject to actual prerequisites; implementation authorized.
