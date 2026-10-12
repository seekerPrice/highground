# Section 12 ticket plan — published mapping source

The user authorized GitHub issue preparation/publication and confirmed Task N gates and original Section 12 granularity. Published in seekerPrice/highground: parent specification #1, Task 1–22 as issues #2–23. Publication is not implementation authorization. The handover source is docs/spec/01-build-spec.md. Attach unresolved notes only to affected tasks; unrelated later questions do not block Task 1. This grouped plan supplied the issue bodies; unresolved proposed changes still require agreement.

Every task after Task 1 is blocked by the preceding task **as a sequencing rule**; this does not claim every preceding task is a technical dependency. The ordered chain is a deliberate user constraint that overrides generic advice to parallelize independent tickets. Every task includes Astra coordination, Sol corrections, relevant local tests and Matt Standards/Spec review against the agreed baseline.

PROPOSED schedule correction: Task 15 follows Task 14 on Thursday; Tasks 16–17 start Friday. Tasks 18–22 are Friday-only Shoulds and may start only after Tasks 1–17 pass on deployed URLs. Stretch features are pitch-only. Do not silently substitute a synthetic feed for a live official feed.


## 01 — Repo + scaffolding

**Blocked by:** No implementation-task blockers; wait for user Task 1 instruction. Future-task decisions do not block scaffolding.

**What it delivers:** Local API health and blank dashboard run from a documented monorepo.

**Acceptance:** API health returns success; frontend opens locally; example environment contains no secrets; no prohibited automation.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 02 — GCP setup script

**Blocked by:** Task 1 complete (ordered execution gate).

**What it delivers:** Repeatable setup provisions the fixed Google Cloud services and secret references.

**Acceptance:** APIs, regional resources, tables and least-privilege identities exist; rerun is safe; credentials stay out of source.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 03 — data.gov.my clients

**Blocked by:** Task 2 complete (ordered execution gate).

**What it delivers:** Actual responses become validated, deduplicated warning observations with freshness and source status.

**Acceptance:** Captured fixtures cover actual schemas, stale/null/error records and marine weather; old DANGER never alerts; device ON/OFF is not severity.

**Proposed issue label:** needs-info — Agree stale-source fallback, freshness threshold and weather geography/type mapping before this behaviour is accepted.

## 04 — Telegram webhook

**Blocked by:** Task 3 complete (ordered execution gate).

**What it delivers:** A real Telegram user reaches the authenticated bot entry point.

**Acceptance:** Correct secret accepted and wrong secret rejected; duplicate updates do not duplicate work; local tunnel setup is documented.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 05 — i18n + onboarding

**Blocked by:** Task 4 complete (ordered execution gate).

**What it delivers:** Owner selects one of eight languages, confirms location and shop/vehicle details, optionally links a worker.

**Acceptance:** Shop persists across restart; address fallback confirms a pin; recipient opts in; eight static templates preserve placeholders; review status is honest; risk unknowns are not invented.

**Proposed issue label:** needs-info — Confirm static Danger wording/placeholder rules, risk unknowns and recipient-linking flow.

## 06 — ADK skeleton

**Blocked by:** Task 5 complete (ordered execution gate).

**What it delivers:** Coordinator routes a fake warning through the specified sub-agents with inspectable decisions.

**Acceptance:** Local fake warning completes; contracts are typed/validated; state persistence approach is explicit; no future feature is represented as implemented.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 07 — Alert dispatch

**Blocked by:** Task 6 complete (ordered execution gate).

**What it delivers:** A simulated event reaches eligible recipients and appears in event/alert records.

**Acceptance:** Radius selection works; recipients receive their language; Pub/Sub is visibly used; BigQuery records sends; Danger bypasses generated text; demo access policy is applied.

**Proposed issue label:** needs-info — Confirm fixed Danger variant, action deadlines and public demo access policy.

## 08 — Safe points + vehicle rescue

**Blocked by:** Task 7 complete (ordered execution gate).

**What it delivers:** Alerts include sourced parking/evacuation destinations and record vehicle confirmations.

**Acceptance:** No invented places/opening claims; destination missing fallback works; vehicle action deadline precedes stock; repeated/worker taps cannot count one vehicle twice.

**Proposed issue label:** needs-info — Confirm destination fallback and deadline policy; sourced place data required.

## 09 — Evidence ledger + neighbour reports

**Blocked by:** Task 8 complete (ordered execution gate).

**What it delivers:** Uploaded photos preserve downloaded bytes, record hashes and produce validated nearby alerts.

**Acceptance:** All media uses shared ingestion; partial-write retries are recoverable; unrelated photos rejected; reporter excluded; per-shop limit enforced; ledger append protected.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 10 — Danger escalation + polling

**Blocked by:** Task 9 complete (ordered execution gate).

**What it delivers:** Scheduled real-source polling and escalating events use deterministic safety handling.

**Acceptance:** Scheduler OIDC enforced; stale observations excluded; escalation deduplicated; all language Danger paths emit only approved fixed content and route button.

**Proposed issue label:** needs-info — Resolve Danger footer/fallback and stale observation policy.

## 11 — Baseline inventory + lift-first

**Blocked by:** Task 10 complete (ordered execution gate).

**What it delivers:** Video becomes an estimated inventory and ranked lift-first list that warning confirmations reference.

**Acceptance:** Hosted download size handled at 20 MB; visible items only; floor/low rank deterministic; estimate labels present; counted items match immutable action snapshot; duplicate confirmation is harmless.

**Proposed issue label:** needs-info — Resolve displayed items versus confirmation snapshot/value.

## 12 — After-flood report

**Blocked by:** Task 11 complete (ordered execution gate).

**What it delivers:** Owner requests recovery reporting, uploads an after-video and receives an estimated loss report link.

**Acceptance:** Baseline association persists; comparison does not invent items; report confidence/limitations shown; failure/retry does not create duplicate reports.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 13 — Report page

**Blocked by:** Task 12 complete (ordered execution gate).

**What it delivers:** An unguessable report link shows before/after estimates, evidence and a printable report.

**Acceptance:** Evidence verification recomputes stored-byte hash against ledger; mismatch is visible; no authenticity guarantee; private media exposure follows policy; print-to-PDF is usable.

**Proposed issue label:** needs-info — Resolve integrity-badge wording and report/media access policy.

## 14 — First deploy

**Blocked by:** Task 13 complete (ordered execution gate).

**What it delivers:** API and web run on Cloud Run and the phone completes core Must moments.

**Acceptance:** M1/M3/M4/M5/M6 complete against deployed URLs; production webhook and Scheduler work; secrets resolved securely; local deploy path creates no repository automation.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 15 — Dashboard

**Blocked by:** Task 14 complete (ordered execution gate).

**What it delivers:** Map, event feed, protection counters and demo controls show the Must journey.

**Acceptance:** Shop levels, sourced places, parking, event radii and danger zones render; polling updates every three seconds; counters do not duplicate; no private recipient data; unavailable Stretch layers omitted.

**Proposed issue label:** needs-info — Agree Thursday scheduling to satisfy Must deadline; omit Stretch depth dots.

## 16 — Seed demo data + redeploy

**Blocked by:** Task 15 complete (ordered execution gate).

**What it delivers:** Six demo shops make the deployed story reproducible.

**Acceptance:** Two real test accounts and four virtual shops; three vehicles; sourced destinations; reset affects only demo records; synthetic data labelled and redeploy verified.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 17 — Hardening

**Blocked by:** Task 16 complete (ordered execution gate).

**What it delivers:** Deployed Must journey survives expected failures and has usable operational documentation.

**Acceptance:** Gemini timeout/bad schema retries once then explains failure; restart/idempotency verified; logs omit secrets; architecture/setup/screenshots recorded; all Tasks 1–17 rechecked deployed.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 18 — Offline card

**Blocked by:** Task 17 complete (ordered execution gate). Friday only; all Tasks 1–17 deployed and accepted.

**What it delivers:** At Watch or on request, owner receives a multilingual image that can be saved offline.

**Acceptance:** 1080×1920 image renders all scripts; facts/destinations constrained; time/emergency text present; saved-file limitation explained; deployed watch and command tested.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 19 — Insurance check

**Blocked by:** Task 18 complete (ordered execution gate). Friday only; all Tasks 1–17 deployed and accepted.

**What it delivers:** Owner uploads a policy and receives cautious extracted coverage and estimated shortfall information.

**Acceptance:** Evidence-backed extraction; unclear remains unclear; insurer-check reminder fixed; original deleted by default and retention opt-in respected; aggregate dashboard only.

**Proposed issue label:** needs-info — Confirm policy deletion exception to immutable-original retention.

## 20 — Waste sorting

**Blocked by:** Task 19 complete (ordered execution gate). Friday only; all Tasks 1–17 deployed and accepted.

**What it delivers:** Loss report provides item disposal categories and aggregate estimated cleanup volumes.

**Acceptance:** Fixed food-safety wording; dispositions/estimates validated; volumes and configurable lorry capacity aggregate consistently; report/map updated and redeployed.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 21 — /check

**Blocked by:** Task 20 complete (ordered execution gate). Friday only; all Tasks 1–17 deployed and accepted.

**What it delivers:** Any user shares a location to view current nearby warnings and listed destinations.

**Acceptance:** No shop signup needed; two-kilometre search and freshness work; no invented opening/safety claims; absent Stretch open-shops feature omitted.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.

## 22 — Learning loop

**Blocked by:** Task 21 complete (ordered execution gate). Friday only; all Tasks 1–17 deployed and accepted.

**What it delivers:** Owner feedback produces transparent outcome metrics and constrained area calibration.

**Acceptance:** Scheduled outcome prompt works; denominators and nonresponses explicit; multiplier bounds enforced; minimum sample checked; no suppression of authoritative Danger; seeded history labelled; redeployed.

**Proposed issue label:** ready-for-agent — subject to blockers and explicit Task N instruction; not started.
