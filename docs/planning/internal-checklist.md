# Internal delivery checklist

This is the active internal planning checklist; it is not permission to implement. Source: docs/spec/01-build-spec.md (exact handover copy), current user instructions and the verified observations in ../planning-review.md. Proposed changes remain open until agreed.

## Completed preparation

- [x] Read the complete build spec, README and Zhao Wei context.
- [x] Inspect official API responses and relevant Telegram/ADK/Vertex references; record evidence and unresolved limits.
- [x] Read grill-with-docs, grilling, domain-modeling, setup, to-spec, to-tickets and Matt code-review instructions.
- [x] Inspect workspace and installed triage skill; no existing application or agent configuration found at initial inspection.
- [x] Parent created public seekerPrice/highground, initialized local Git, and verified GitHub Actions enabled:false.
- [x] Prepare reviewable setup/spec/ticket/checklist drafts only.

## Decisions and tracking gates

These apply to the affected task; they do not globally block Task 1 scaffolding. Task 1 still awaits the explicit user instruction.

- [x] User confirmed Task N gates remain; prepare setup/spec/tickets now.
- [x] User selected GitHub Issues and authorized Git setup; all tests/builds/deploys remain local with no GitHub CI.
- [x] User approved AGENTS.md and default labels; parent activated agent/tracker/domain/label configuration and verified all five GitHub labels.
- [x] Astra read the active configuration and confirmed Task N gates, fixed stack, local-only verification and no global future-decision blocker.
- [ ] Agree Thursday Task 15 schedule change so every Must is deployed.
- [ ] Agree stale-feed behaviour and live-data claim; fresh official flood input remains unresolved.
- [ ] Settle fixed Danger template wording, no-destination fallback, action deadline policy and exact confirmation semantics.
- [ ] Confirm public/demo/report exposure policy and availability of project/bot/testers/sourced places.
- [ ] Confirm proposed external-behaviour test seams before affected implementation; preserve the user-mandated Section 12 task granularity.
- [x] Parent published specification issue #1 and Task 1–22 issues #2–23; unresolved decisions remain attached to affected tasks. Publication does not authorize implementation.
- [x] Astra checked published Task 1 and Task 18 for parent linkage, Task N gates, no-CI rules and Friday/deployed prerequisites; no implementation is claimed.
- [ ] Establish an agreed review baseline before implementation and use actual non-empty diffs for Matt review.

## Execution contract

Astra coordinates Sol, inspects actual changes and local checks, sends defects back and rechecks corrections before completion is reported. Matt review runs independent Standards and Spec axes; findings return to Sol and are rechecked. A checkbox is marked only with observed evidence. Skill-required review agents run only for actual implementation review, not to create premature implementation. No Sol implementation has begun.

The ordered workflow remains Tasks 1–22, with explicit user confirmation before each next task. Thursday includes all Musts; Friday Shoulds require deployed Tasks 1–17. Stretch is pitch-only. Review policy proposal: each task uses its approved baseline, with full integration review after Task 17; agree the baseline protocol before coding.

## Per-task gates

### Task 1 — Repo + scaffolding

Scope: Must/foundation. Deliverable: Local API health and blank dashboard run from a documented monorepo.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 2 — GCP setup script

Scope: Must/foundation. Deliverable: Repeatable setup provisions the fixed Google Cloud services and secret references.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 3 — data.gov.my clients

Scope: Must/foundation. Deliverable: Actual responses become validated, deduplicated warning observations with freshness and source status.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 4 — Telegram webhook

Scope: Must/foundation. Deliverable: A real Telegram user reaches the authenticated bot entry point.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 5 — i18n + onboarding

Scope: Must/foundation. Deliverable: Owner selects one of eight languages, confirms location and shop/vehicle details, optionally links a worker.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 6 — ADK skeleton

Scope: Must/foundation. Deliverable: Coordinator routes a fake warning through the specified sub-agents with inspectable decisions.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 7 — Alert dispatch

Scope: Must/foundation. Deliverable: A simulated event reaches eligible recipients and appears in event/alert records.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 8 — Safe points + vehicle rescue

Scope: Must/foundation. Deliverable: Alerts include sourced parking/evacuation destinations and record vehicle confirmations.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 9 — Evidence ledger + neighbour reports

Scope: Must/foundation. Deliverable: Uploaded photos preserve downloaded bytes, record hashes and produce validated nearby alerts.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 10 — Danger escalation + polling

Scope: Must/foundation. Deliverable: Scheduled real-source polling and escalating events use deterministic safety handling.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 11 — Baseline inventory + lift-first

Scope: Must/foundation. Deliverable: Video becomes an estimated inventory and ranked lift-first list that warning confirmations reference.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 12 — After-flood report

Scope: Must/foundation. Deliverable: Owner requests recovery reporting, uploads an after-video and receives an estimated loss report link.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 13 — Report page

Scope: Must/foundation. Deliverable: An unguessable report link shows before/after estimates, evidence and a printable report.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 14 — First deploy

Scope: Must/foundation. Deliverable: API and web run on Cloud Run and the phone completes core Must moments.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 15 — Dashboard

Scope: Must/foundation. Deliverable: Map, event feed, protection counters and demo controls show the Must journey.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 16 — Seed demo data + redeploy

Scope: Must/foundation. Deliverable: Six demo shops make the deployed story reproducible.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 17 — Hardening

Scope: Must/foundation. Deliverable: Deployed Must journey survives expected failures and has usable operational documentation.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 18 — Offline card

Scope: Should — Friday and deployed Tasks 1–17 required. Deliverable: At Watch or on request, owner receives a multilingual image that can be saved offline.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 19 — Insurance check

Scope: Should — Friday and deployed Tasks 1–17 required. Deliverable: Owner uploads a policy and receives cautious extracted coverage and estimated shortfall information.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 20 — Waste sorting

Scope: Should — Friday and deployed Tasks 1–17 required. Deliverable: Loss report provides item disposal categories and aggregate estimated cleanup volumes.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 21 — /check

Scope: Should — Friday and deployed Tasks 1–17 required. Deliverable: Any user shares a location to view current nearby warnings and listed destinations.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.

### Task 22 — Learning loop

Scope: Should — Friday and deployed Tasks 1–17 required. Deliverable: Owner feedback produces transparent outcome metrics and constrained area calibration.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] User next-task gate satisfied.
