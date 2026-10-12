# Internal delivery checklist

This is the active delivery checklist under the user's authorization to implement all tasks. Source: docs/spec/01-build-spec.md (exact handover copy), current user instructions and the verified observations in ../planning-review.md. Proposed changes remain open until agreed.

## Completed preparation

- [x] Read the complete build spec, README and Zhao Wei context.
- [x] Inspect official API responses and relevant Telegram/ADK/Vertex references; record evidence and unresolved limits.
- [x] Read grill-with-docs, grilling, domain-modeling, setup, to-spec, to-tickets and Matt code-review instructions.
- [x] Inspect workspace and installed triage skill; no existing application or agent configuration found at initial inspection.
- [x] Parent created public seekerPrice/highground, initialized local Git, and verified GitHub Actions enabled:false.
- [x] Prepare reviewable setup/spec/ticket/checklist drafts only.

## Decisions and tracking gates

These apply to the affected task; they do not globally block Task 1 scaffolding. All tasks are now authorized; actual technical dependencies and the local Must gate govern progression.

- [x] Earlier Task N gates were superseded by the latest user instruction: implement all tasks and parallelize where possible.
- [x] User selected GitHub Issues and authorized Git setup; all tests/builds/deploys remain local with no GitHub CI.
- [x] User approved AGENTS.md and default labels; parent activated agent/tracker/domain/label configuration and verified all five GitHub labels.
- [x] Astra read the active configuration and confirmed authorization/dependency rules, fixed stack, local-only verification and no global future-decision blocker.
- [x] Q1 accepted: Task 15 follows Task 14 for the Must deployment target; dates allow earlier progress.
- [x] Q2 accepted: stale/unavailable source status and explicitly labelled demo simulations; no claim of validated live official flood warnings. Fresh source discovery remains open for Task 3.
- [x] Q3 accepted: fixed Danger footer/fallback and two deterministic action targets, vehicle first; no safety/arrival-time guarantees.
- [ ] Settle exact translations/placeholders, target configuration and confirmation semantics in their respective tasks.
- [x] User approved synthetic-only public data, operator token, bearer reports/private media, integrity label and exact confirmation snapshots.
- [x] User approved 90-minute freshness and 15/30-minute action targets.
- [x] Constrained Warning composition adopted under the user's five-minute default; configured Gemini selects approved localized structures with deterministic facts and fixed fallback. Free-form narrowing is explicit in approved-decisions.md.
- [x] Root established dedicated project/billing, bot access and local emulators; configured Vertex models passed real calls.
- [x] Six explicitly synthetic shops, the consenting own-chat and virtual recipients are the approved local acceptance scope; adopted after the five-minute decision window. Actual second-phone and hosted acceptance remain pending.
- [x] Two historical destination sources and coordinates reviewed; current opening and parking floor remain unknown and are labelled accordingly.
- [ ] Confirm proposed external-behaviour test seams before affected implementation; preserve the user-mandated Section 12 task granularity.
- [x] Parent published specification issue #1 and Task 1–22 issues #2–23; unresolved decisions remain attached to affected tasks. Publication was followed by explicit user authorization to implement all tasks.
- [x] Astra checked published Task 1 and Task 18 for parent linkage, Task N gates, no-CI rules and deployed prerequisites (calendar gate later removed by user); no implementation is claimed.
- [x] Capture Task 1 review baseline bb1b098 (same tree as task-start GitButler workspace HEAD); use its non-empty committed diff for Matt review.

## Execution contract

Astra coordinates Sol, inspects actual changes and local checks, sends defects back and rechecks corrections before completion is reported. Matt review runs independent Standards and Spec axes; findings return to Sol and are rechecked. A checkbox is marked only with observed evidence. Skill-required review agents run only for actual implementation review, not to create premature implementation. Task 1 implementation, local acceptance and both review axes are complete. Foundation Tasks 2/3/4/6 passed local checks and both independent Matt axes after the privacy correction (final 69 API tests). Tasks 3/4/6 local acceptance is complete; Task 2 cloud provisioning remains deferred. Tasks 5/7 local acceptance and both Matt axes passed against final candidate 8818a93. Tasks 8/9 implementation and both Matt axes passed through 1a4d7b1; the complete local gate passed 6 infrastructure and 175 API tests with frontend checks. Task 8 live own-chat acceptance passed; Task 9 integrated local acceptance passed with actual service emulators/configured Flash and explicitly virtual Telegram edges. Actual Telegram photo upload remains pending consent. Tasks 10/11 local acceptance is complete at 8d28cc8: 243 API tests, final Standards 0 and Spec 0, plus actual local polling and configured-Pro service integration with synthetic Telegram edges. Tasks 12/13/15 implementation from ca6cd6f is frozen after correcting the concurrent polling and optional confirmation-outbox failures found by the combined gate. Recovery/report backend and report/dashboard UI have focused checks plus actual Pro/production-browser evidence; the final local gate passed 6 infrastructure, 283 API and 14 frontend tests plus lint/type/build; independent final reviews passed Standards0/Spec0 at f914f9a; report print and Task 16 reset-generation boundary remain outstanding. Task14 packaging, Task16 scenario backend/frontend and Task17 local lifecycle, initializer, exact query cleanup and protected manual recovery are implemented from6ccc9b. Focused component checks and Astra correction review passed; the initial combined full gate at8be5884 passed 24 infrastructure, 332 API and 19 frontend tests with no skips, plus lint/type/build. Independent Standards1/Spec2 findings exposed fixture ownership/Danger routing and reset history recovery defects; the corrected focused gate passed37 cases and Astra rechecked nine targeted cases. The corrected full gate atf6efd315 passed24 infrastructure,339 API (five dependency warnings),19 frontend tests with no skips, plus lint/type/build; both independent correction reviews finished with Standards0/Spec0 outstanding. Root restored all four bounded local services with verified original-media preservation; the actual protected factory/manual recovery, shared virtual reset/retry journey and one consenting owner’s immutable vehicle/stock confirmations passed; see task-17-operational-verification.md. Actual PDF/print remains the open local Must gate. Hosting and real second-phone/media-upload acceptance remain deferred.

The active technical graph is in dependency-plan.md; Task numbers remain traceability labels. Independent work may proceed in parallel without new Task N approval. Dates are targets and work may finish earlier; Shoulds may start earlier than Friday only after all Must behaviour is locally verified; hosting is deferred. Stretch is pitch-only. Review uses each task-start committed baseline; Task 1 baseline is bb1b098. User authorization includes the review/correction loop.

## Per-task gates

### Task 1 — Repo + scaffolding

Scope: Must/foundation. Deliverable: Local API health and blank dashboard run from a documented monorepo.

- [x] Astra task brief written; user-authorized scope and acceptance clear; blockers satisfied.
- [x] Sol implemented only Task 1 scaffold.
- [x] Relevant local checks passed; results recorded in task-01-verification.md.
- [x] Astra inspected actual source, real health HTTP response and rendered browser page; Sol lint correction passed the final gate.
- [x] Matt Standards review completed against bb1b098...71cbc75: no actionable findings.
- [x] Matt Spec review completed against bb1b098...71cbc75: no actionable findings.
- [x] Task 1 local acceptance met; evidence in task-01-verification.md. No deployment belongs to this task.
- [x] User authorized progression to all tasks; Tasks 2 and 3 dispatched in parallel.

### Task 2 — GCP setup script

Status: implemented and Astra locally verified (syntax and six command-contract tests); independent Matt review passed. Cloud provisioning remains deferred.

Scope: Must/foundation. Deliverable: Repeatable setup provisions the fixed Google Cloud services and secret references.

- [x] Astra brief recorded in tasks-02-03-brief.md; implementation authorized and dispatched.
- [x] Sol implemented the assigned slice.
- [x] Focused local checks passed; results captured in infrastructure/data research notes.
- [x] Astra inspected actual files, returned defects to Sol and independently reran affected checks after corrections.
- [x] Matt Standards review completed; unused raw inbox payload corrected and independently rechecked where relevant.
- [x] Matt Spec review completed; zero actionable findings.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 3 — data.gov.my clients

Status: implemented and Astra locally verified (33 API tests). Recovery namespace/watermark corrections pass. Independent Matt review passed; live official source/timezone attribution limitations remain explicit.

Scope: Must/foundation. Deliverable: Actual responses become validated, deduplicated warning observations with freshness and source status.

- [x] Astra brief recorded in tasks-02-03-brief.md; implementation authorized and dispatched.
- [x] Sol implemented the assigned slice.
- [x] Focused local checks passed; results captured in infrastructure/data research notes.
- [x] Astra inspected actual files, returned defects to Sol and independently reran affected checks after corrections.
- [x] Matt Standards review completed; unused raw inbox payload corrected and independently rechecked where relevant.
- [x] Matt Spec review completed; zero actionable findings.
- [x] Local task acceptance met with evidence; external limitations are recorded separately.
- [x] Technical prerequisites for dependent local work met.

### Task 4 — Telegram webhook

Scope: Must/foundation. Deliverable: A real Telegram user reaches the authenticated bot entry point.

- [x] Astra brief recorded in tasks-04-06-brief.md; dispatched with explicit shared-file ownership.
- [x] Sol implemented the assigned task slice.
- [x] Relevant local checks pass; evidence in foundation-verification.md.
- [x] Astra inspected actual files, returned defects and independently rechecked corrected code.
- [x] Matt Standards review completed; unused raw inbox payload corrected and independently rechecked where relevant.
- [x] Matt Spec review completed; zero actionable findings.
- [x] Local task acceptance met with evidence; external limitations are recorded separately.
- [x] Technical prerequisites for dependent local work met.

### Task 5 — i18n + onboarding

Scope: Must/foundation. Deliverable: Owner selects one of eight languages, confirms location and shop/vehicle details, optionally links a worker.

- [x] Astra brief task-05-brief.md written; dispatched in parallel from baseline 4666575 with shared-file ownership.
- [x] Sol implemented the onboarding/i18n slice and corrections.
- [x] Astra's affected local check passed 46 tests; actual own-chat registration passed. Evidence: tasks-05-07-verification.md and task-05-live-verification.md.
- [x] Astra inspected actual files, returned defects and independently rechecked corrections.
- [x] Matt Standards review completed against 4666575…8818a93; zero actionable findings.
- [x] Matt Spec review completed against 4666575…8818a93; zero actionable findings.
- [x] Local task acceptance met with recorded evidence; native translation/two-phone/cloud boundaries remain explicit.
- [x] Technical prerequisites for dependent local work met.

### Task 6 — ADK skeleton

Scope: Must/foundation. Deliverable: Coordinator routes a fake warning through the specified sub-agents with inspectable decisions.

- [x] Astra brief recorded in tasks-04-06-brief.md; dispatched with explicit shared-file ownership.
- [x] Sol implemented the assigned task slice.
- [x] Relevant local checks pass; evidence in foundation-verification.md.
- [x] Astra inspected actual files, returned defects and independently rechecked corrected code.
- [x] Matt Standards review completed; unused raw inbox payload corrected and independently rechecked where relevant.
- [x] Matt Spec review completed; zero actionable findings.
- [x] Local task acceptance met with evidence; external limitations are recorded separately.
- [x] Technical prerequisites for dependent local work met.

### Task 7 — Alert dispatch

Scope: Must/foundation. Deliverable: A simulated event reaches eligible recipients and appears in event/alert records.

- [x] Astra brief task-07-brief.md written; dispatched in parallel from baseline 4666575 with shared-file ownership.
- [x] Sol implemented the dispatch slice and corrections.
- [x] Final backend suite passed 121 tests with actual Firestore/Pub/Sub/BigQuery integration; real ADK selection and cold fallback measured separately. Evidence: tasks-05-07-verification.md.
- [x] Astra inspected source and results, returned defects and rechecked corrections.
- [x] Matt Standards review completed against 4666575…8818a93; zero actionable findings.
- [x] Matt Spec review completed against 4666575…8818a93; zero actionable findings.
- [x] Local task acceptance met with recorded evidence; native translation/two-phone/cloud boundaries remain explicit.
- [x] Technical prerequisites for dependent local work met.

### Task 8 — Safe points + vehicle rescue

Scope: Must/foundation. Deliverable: Alerts include sourced parking/evacuation destinations and record vehicle confirmations.

- [x] Astra brief tasks-08-09-brief.md recorded; dispatched in parallel from reviewed baseline 8818a93 with shared-file ownership.
- [x] Sol implemented the bounded Task 8 candidate; shared Task 9 webhook wiring is included.
- [x] Focused checks and final complete local gate recorded: 6 infrastructure + 175 API tests, no skips, frontend checks passed at 1a4d7b1.
- [x] Astra inspected actual Task 8 files, rechecked corrections and independently passed 30 vehicle/webhook tests.
- [x] Matt Standards: all findings corrected and independently rechecked; zero outstanding through 1a4d7b1.
- [x] Matt Spec: all findings corrected and independently rechecked; zero outstanding through 1a4d7b1.
- [x] Local Task 8 acceptance: real own-chat routes, vehicle confirmation, repeated-click dedupe and preview correction verified. Hosted acceptance remains deferred.
- [x] Technical prerequisites for Tasks 10/11 met; external acceptance limits remain explicitly recorded.

### Task 9 — Evidence ledger + neighbour reports

Scope: Must/foundation. Deliverable: Uploaded photos preserve downloaded bytes, record hashes and produce validated nearby alerts.

- [x] Astra brief tasks-08-09-brief.md recorded; dispatched in parallel from reviewed baseline 8818a93 with shared-file ownership.
- [x] Sol implemented the bounded Task 9 candidate and froze it for integrated acceptance.
- [x] Focused/configured multimodal checks and full all-emulator gate passed after persistent BigQuery recovery: 6 infrastructure + 175 API tests, no skips, frontend checks passed.
- [x] Astra inspected actual files, returned/rechecked corrections and independently passed 22 photo/persisted-payload tests (one BigQuery test explicitly deselected).
- [x] Matt Standards: all findings corrected and independently rechecked; zero outstanding through 1a4d7b1.
- [x] Matt Spec: all findings corrected and independently rechecked; zero outstanding through 1a4d7b1.
- [x] Local Task 9 journey acceptance passed against frozen 1a4d7b1 with actual Firestore/GCS/BigQuery/Flash ADK and synthetic download/virtual Telegram edges: immutable receipt, confirmed location, Danger fanout, replay dedupe and hash verification.
- [ ] Actual Telegram photo upload remains pending explicit upload consent; real neighbour-delivery latency, hosted and second-phone acceptance remain deferred.
- [x] Technical prerequisites for Tasks 10/11 met; external acceptance limits remain explicitly recorded.

### Task 10 — Danger escalation + polling

Scope: Must/foundation. Deliverable: Scheduled real-source polling and escalating events use deterministic safety handling.

- [x] Astra dispatched the bounded task brief from reviewed baseline 1a4d7b1; parallel lanes coordinate shared risk/episode interfaces and files.
- [x] Sol implemented the bounded task slice and froze it for review.
- [x] The final 243-test API gate passed at 8d28cc8; actual polling/model service probes and limits are recorded in tasks-10-11-verification.md.
- [x] Astra inspected actual files, returned concrete defects and independently rechecked corrections.
- [x] Matt Standards review completed; final correction recheck has 0 outstanding findings.
- [x] Matt Spec review completed; final correction recheck has 0 outstanding findings.
- [x] Local acceptance met with recorded evidence; hosting and external acceptance limits remain deferred.
- [x] Technical prerequisites for dependent Must work met; pending external acceptance remains explicitly recorded.

### Task 11 — Baseline inventory + lift-first

Scope: Must/foundation. Deliverable: Video becomes an estimated inventory and ranked lift-first list that warning confirmations reference.

- [x] Astra dispatched the bounded task brief from reviewed baseline 1a4d7b1; parallel lanes coordinate shared risk/episode interfaces and files.
- [x] Sol implemented the bounded task slice and froze it for review.
- [x] The final 243-test API gate passed at 8d28cc8; actual polling/model service probes and limits are recorded in tasks-10-11-verification.md.
- [x] Astra inspected actual files, returned concrete defects and independently rechecked corrections.
- [x] Matt Standards review completed; final correction recheck has 0 outstanding findings.
- [x] Matt Spec review completed; final correction recheck has 0 outstanding findings.
- [x] Local acceptance met with recorded evidence; hosting and external acceptance limits remain deferred.
- [x] Technical prerequisites for dependent Must work met; pending external acceptance remains explicitly recorded.

### Task 12 — After-flood report

Scope: Must/foundation. Deliverable: Owner requests recovery reporting, uploads an after-video and receives an estimated loss report link.

- [x] Astra dispatched the shared typed-interface brief from ca6cd6f; backend/frontend file ownership and local acceptance are explicit.
- [x] Sol implemented the bounded backend slice; recorded local acceptance and reviews are complete.
- [x] Focused local checks and actual service/UI evidence are recorded in tasks-12-13-15-verification.md; the final combined gate passed 6 infrastructure/283 API/14 frontend tests plus lint/type/build after diagnosed corrections and emulator recovery.
- [x] Astra inspected the implemented component, returned defects and independently rechecked corrections.
- [x] Matt Standards completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Matt Spec completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Local backend acceptance met with actual-model/service and corrected-contract evidence; hosting remains deferred.
- [x] Technical prerequisites for dependent Must work met; external acceptance limits remain recorded.

### Task 13 — Report page

Scope: Must/foundation. Deliverable: An unguessable report link shows before/after estimates, evidence and a printable report.

- [x] Astra dispatched the shared typed-interface brief from ca6cd6f; backend/frontend file ownership and local acceptance are explicit.
- [x] Sol implemented and froze the bounded task slice; acceptance remains pending the gates below.
- [x] Focused local checks and actual service/UI evidence are recorded in tasks-12-13-15-verification.md; the final combined gate passed 6 infrastructure/283 API/14 frontend tests plus lint/type/build after diagnosed corrections and emulator recovery.
- [x] Astra inspected the implemented component, returned defects and independently rechecked corrections.
- [x] Matt Standards completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Matt Spec completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Additional production browser checks passed: mobile width, keyboard use, actual file integrity and isolated adapter failure/unknown/partial states; see [UI verification](tasks-13-15-ui-verification.md). Adapters establish UI behavior, not actual backend outages.
- [ ] Local acceptance: PDF/print output still requires desktop unlock; latest contract amendments passed the f6efd315 combined gate and independent reviews. Hosting remains deferred.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 14 — First deploy

Scope: Must/foundation. Deliverable: API and web run on Cloud Run and the phone completes core Must moments.

- [x] Astra dispatched the bounded local-first brief from6ccc9b, with disjoint ownership and root-controlled runtime operations.
- [x] Sol applied six packaging files byte-for-byte from the tested staging candidate; hosting is deferred.
- [x] Four fake-command packaging tests, observed authorization-guard RED/GREEN and root actual final-source image/runtime checks are recorded in task-14-verification.md.
- [x] Astra read the actual packaging/helper files and evidence, corrected public documentation paths, and found no functional packaging defect; independent correction review passed atf6efd315.
- [x] Matt Standards completed: original finding corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Matt Spec completed: both original findings corrected; independent f6efd315 recheck has zero outstanding findings.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 15 — Dashboard

Scope: Must/foundation. Deliverable: Map, event feed, protection counters and demo controls show the Must journey.

- [x] Astra dispatched the shared typed-interface brief from ca6cd6f; backend/frontend file ownership and local acceptance are explicit.
- [x] Dashboard map/feed/BigQuery metrics and operator UI now include Task16 scenario-generation reset and bounded superseded-response handling; the final shared browser/operator journey passed (task-17-operational-verification.md).
- [x] Focused local checks and actual service/UI evidence are recorded in tasks-12-13-15-verification.md; the final combined gate passed 6 infrastructure/283 API/14 frontend tests plus lint/type/build after diagnosed corrections and emulator recovery.
- [x] Astra inspected the implemented component, returned defects and independently rechecked corrections. Production mobile/keyboard, unavailable/empty/retry UI checks passed through an explicit temporary adapter; see [UI verification](tasks-13-15-ui-verification.md).
- [x] Matt Standards completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Matt Spec completed for the current component; final f914f9a recheck has zero outstanding findings.
- [x] Local dashboard acceptance passed: actual shared six-virtual Warning/Danger/reset, lost-response/superseded/new-intent retry and one consenting owner’s duplicate-safe vehicle/stock confirmations; see task-17-operational-verification.md. Hosted acceptance remains deferred.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 16 — Seed demo data + redeploy

Scope: Must/foundation. Deliverable: Six demo shops make the deployed story reproducible.

- [x] Astra dispatched the bounded local-first brief from6ccc9b, with disjoint ownership and root-controlled runtime operations.
- [x] Sol implemented the six-shop/three-vehicle synthetic fixtures, explicit virtual delivery, immutable fixture receipts, stable reset requests and guarded scenario generations; alerts-only real-recipient binding is explicit.
- [x] Focused Task 16 checks and observed RED/GREEN reset corrections are recorded in [verification](task-16-verification.md): 116 passed with one explicitly missing-endpoint stock integration skip; final scenario/dashboard checks passed all 26 cases. Root isolated actual four-service seed/router/reset journey passed in 24.584s with six originals/ledger identities and zero Telegram/model calls; see [SDK verification](task-16-sdk-verification.md). The corrected full gate passed24 infrastructure/339 API/19 frontend tests with no skips; shared global binding/operator acceptance subsequently passed, including preserved ordinary owner lookup and duplicate-safe real callbacks (task-17-operational-verification.md).
- [x] Astra inspected actual files, returned duplicate-reset/partial-seed and virtual-response defects, rechecked fixes, and independently passed 26 scenario/dashboard cases in 1.54s and the final 12 frontend contract/operator cases. The superseded-response regression accepts only known bounded reason values and permits a fresh simulation intent after reset.
- [x] Matt Standards completed: original finding corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Matt Spec completed: both original findings corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Local scenario acceptance passed with actual service seeding, six virtual recipients, explicit consenting-owner binding, retained ordinary ownership, current-generation reset/retry and exact duplicate-safe action facts. Redeployment remains deferred.
- [x] Technical prerequisites for dependent local work met; second-phone/media-upload/hosting limitations remain explicit. This does not close the PDF-dependent full Must gate.

### Task 17 — Hardening

Scope: Must/foundation. Deliverable: Deployed Must journey survives expected failures and has usable operational documentation.

- [x] Astra dispatched the bounded local-first brief from6ccc9b, with disjoint ownership and root-controlled runtime operations.
- [x] Sol implemented lifecycle/strict-gate controls, non-destructive resource initialization, exact current-query cleanup, integration setup hygiene and authenticated bounded manual outbox recovery; no automatic schedule was created.
- [x] Focused checks passed: Astra independently ran the 18-test infrastructure slice and six initializer cases; root actual initializer dry-run/apply/repeat and isolated four-service scenario probes passed. Sol final recovery/Scheduler/dashboard/query gate passed 29 tests with no skips; Astra independently passed 13 protected-route/dashboard cases in 1.92s. The corrected combined full gate passed24 infrastructure/339 API/19 frontend tests with no skips; see task-17-recovery-verification.md and task-16-sdk-verification.md.
- [x] Astra inspected actual lifecycle, initializer, query, cleanup, resumer and dashboard code; returned the missing fresh-BigQuery path and empty optional endpoint defect, then rechecked focused corrections. Root migration preservation is recorded in local-runtime-migration.md. Both independent Matt correction reviews passed atf6efd315; actual factory/manual recovery and shared operator acceptance subsequently passed; the complete local Must gate still awaits PDF/print (task-17-operational-verification.md).
- [x] Matt Standards completed: original finding corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Matt Spec completed: both original findings corrected; independent f6efd315 recheck has zero outstanding findings.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 18 — Offline card

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: At Watch or on request, owner receives a multilingual image that can be saved offline.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 19 — Insurance check

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Owner uploads a policy and receives cautious extracted coverage and estimated shortfall information.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 20 — Waste sorting

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Loss report provides item disposal categories and aggregate estimated cleanup volumes.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 21 — /check

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Any user shares a location to view current nearby warnings and listed destinations.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.

### Task 22 — Learning loop

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Owner feedback produces transparent outcome metrics and constrained area calibration.

- [ ] Astra task brief and acceptance agreed; blockers satisfied.
- [ ] Sol implements only this task.
- [ ] Relevant local checks run; results captured.
- [ ] Astra inspects files and results, returns defects to Sol, and rechecks corrections.
- [ ] Matt Standards review completed; relevant findings corrected and rechecked.
- [ ] Matt Spec review completed; relevant findings corrected and rechecked.
- [ ] Acceptance met, deployment verified where required, and completion reported with evidence.
- [ ] Technical prerequisites for dependent work met; external acceptance evidence recorded where required.
