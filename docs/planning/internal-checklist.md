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

Astra coordinates Sol, inspects actual changes and local checks, sends defects back and rechecks corrections before completion is reported. Matt review runs independent Standards and Spec axes; findings return to Sol and are rechecked. A checkbox is marked only with observed evidence. Skill-required review agents run only for actual implementation review, not to create premature implementation. Task 1 implementation, local acceptance and both review axes are complete. Foundation Tasks 2/3/4/6 passed local checks and both independent Matt axes after the privacy correction (final 69 API tests). Tasks 3/4/6 local acceptance is complete; Task 2 cloud provisioning remains deferred. Tasks 5/7 local acceptance and both Matt axes passed against final candidate 8818a93. Tasks 8/9 implementation and both Matt axes passed through 1a4d7b1; the complete local gate passed 6 infrastructure and 175 API tests with frontend checks. Task 8 live own-chat acceptance passed; Task 9 integrated local acceptance passed with actual service emulators/configured Flash and explicitly virtual Telegram edges. Actual Telegram photo upload remains pending consent. Tasks 10/11 local acceptance is complete at 8d28cc8: 243 API tests, final Standards 0 and Spec 0, plus actual local polling and configured-Pro service integration with synthetic Telegram edges. Tasks 12/13/15 implementation from ca6cd6f is frozen after correcting the concurrent polling and optional confirmation-outbox failures found by the combined gate. Recovery/report backend and report/dashboard UI have focused checks plus actual Pro/production-browser evidence; the final local gate passed 6 infrastructure, 283 API and 14 frontend tests plus lint/type/build; independent final reviews passed Standards0/Spec0 at f914f9a; report print and Task 16 reset-generation boundary remain outstanding. Task14 packaging, Task16 scenario backend/frontend and Task17 local lifecycle, initializer, exact query cleanup and protected manual recovery are implemented from6ccc9b. Focused component checks and Astra correction review passed; the initial combined full gate at8be5884 passed 24 infrastructure, 332 API and 19 frontend tests with no skips, plus lint/type/build. Independent Standards1/Spec2 findings exposed fixture ownership/Danger routing and reset history recovery defects; the corrected focused gate passed37 cases and Astra rechecked nine targeted cases. The corrected full gate atf6efd315 passed24 infrastructure,339 API (five dependency warnings),19 frontend tests with no skips, plus lint/type/build; both independent correction reviews finished with Standards0/Spec0 outstanding. Root restored all four bounded local services with verified original-media preservation; the actual protected factory/manual recovery, shared virtual reset/retry journey and one consenting owner’s immutable vehicle/stock confirmations passed; see task-17-operational-verification.md. The native PDF correction at5be7f18 subsequently passed actual export, full24/339/19 local gate and independent Standards0/Spec0; local Must acceptance is now complete. Hosting and real second-phone/media-upload acceptance remain deferred.

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
- [x] Local acceptance: native PDF export succeeded after desktop unlock, but all three receipt hashes/byte counts were absent (actual-PDF regression exit1). Sol supplied a two-file print-only receipt correction; actual native export now passes: two A4 pages, all three full hashes exactly once, byte counts and disclaimers present, capability absent; Root and Astra visually inspected both pages. Independent correction reviews now pass Standards0/Spec0 at5be7f18. The first subsequent full gate stopped at334 API passes/five failures: four exact BigQuery cleanup failures with correct rows, plus one Firestore concurrent-claim lock timeout; bounded copy-only BQ recovery preserved business/job data, and the final full gate passed24infra/339API/19web plus lint/type/build with no skips. Three actual factory dashboard reads kept dataset count4→4. No backend changes were needed. Hosting remains deferred.
- [x] Technical prerequisites for dependent local work met; hosting and separately deferred external acceptance remain explicit.

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
- [x] Technical prerequisites for dependent local work met; second-phone/media-upload/hosting limitations remain explicit. The PDF-dependent full local Must gate subsequently passed at5be7f18.

### Task 17 — Hardening

Scope: Must/foundation. Deliverable: Deployed Must journey survives expected failures and has usable operational documentation.

- [x] Astra dispatched the bounded local-first brief from6ccc9b, with disjoint ownership and root-controlled runtime operations.
- [x] Sol implemented lifecycle/strict-gate controls, non-destructive resource initialization, exact current-query cleanup, integration setup hygiene and authenticated bounded manual outbox recovery; no automatic schedule was created.
- [x] Focused checks passed: Astra independently ran the 18-test infrastructure slice and six initializer cases; root actual initializer dry-run/apply/repeat and isolated four-service scenario probes passed. Sol final recovery/Scheduler/dashboard/query gate passed 29 tests with no skips; Astra independently passed 13 protected-route/dashboard cases in 1.92s. The corrected combined full gate passed24 infrastructure/339 API/19 frontend tests with no skips; see task-17-recovery-verification.md and task-16-sdk-verification.md.
- [x] Astra inspected actual lifecycle, initializer, query, cleanup, resumer and dashboard code; returned the missing fresh-BigQuery path and empty optional endpoint defect, then rechecked focused corrections. Root migration preservation is recorded in local-runtime-migration.md. Both independent Matt correction reviews passed atf6efd315; actual factory/manual recovery and shared operator acceptance subsequently passed; the complete local Must gate subsequently passed native PDF/full verification and Standards0/Spec0 at5be7f18 (task-17-operational-verification.md).
- [x] Matt Standards completed: original finding corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Matt Spec completed: both original findings corrected; independent f6efd315 recheck has zero outstanding findings.
- [x] Local acceptance met at5be7f18 after actual native PDF and recovered-runtime checks; cloud deployment remains explicitly deferred.
- [x] Full local Must gate accepted; Should work may start. Separately deferred external acceptance remains recorded.

### Task 18 — Offline card

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: At Watch or on request, owner receives a multilingual image that can be saved offline.

- [x] Preparatory file/interface/test brief written in tasks-18-22-brief.md; source and current modules inspected. Planning only.
- [x] Astra dispatched Sol Task18 from831c366: card modules/assets/tests and initial shared integration implemented; candidate frozen, focused checks/rendering/received-image evidence recorded, independent reviews cleared; final complete local gate passed24infra/467API/22frontend plus lint/type/build.
- [x] Host/Linux shaping and all eight rendered card variants checked; native-language wording review remains pending. See tasks-18-19-verification.md.
- [x] User explicitly authorized the prepared synthetic Telegram card photo; actual send, visible receipt, downloaded JPEG and local visual inspection passed. Derived-image re-encoding and no airplane-mode claim are recorded in tasks-18-19-verification.md.
- [x] Astra task brief and local acceptance agreed; local blockers satisfied. The user approved constrained card wording and the local Must gate passed; actual implementation/integration evidence and final24infra/467API/22frontend gate passed. Separately deferred external limits remain explicit.
- [x] Sol implementation for this task is frozen within the shared Task18/19 boundary.
- [x] Final local checks passed24infra/467API/22frontend, zero skips, plus lint/type/build; results captured in tasks-18-19-verification.md.
- [x] Astra inspected files/results, returned defects, and rechecked corrections. Exact RED/GREEN evidence is recorded in tasks-18-19-verification.md.
- [x] Matt Standards review completed; final recheck0 remaining at manifest83b211c12eb41fe7c7f62ea7f25ad8d832a966c702fff39e3aecebd2f9b68af4.
- [x] Matt Spec review completed; final recheck0 remaining at the same frozen snapshot.
- [x] Local acceptance met and evidence recorded at1646ebc/PR29; hosting remains explicitly deferred.
- [x] Technical prerequisites for dependent local work met; native wording/offline-phone/hosting limits remain recorded. Root released Tasks20–22 execution from1646ebc.

### Task 19 — Insurance check

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Owner uploads a policy and receives cautious extracted coverage and estimated shortfall information.

- [x] Preparatory file/interface/test brief written in tasks-18-22-brief.md; source and current modules inspected. Planning only.
- [x] Astra dispatched the parallel Sol policy domain lane from831c366; shared integration followed the explicit Task18 handoff. Backend/frontend candidates are frozen, with114 policy cases and bounded multi-photo/PDF intake, disclosure and exact retention semantics recorded; actual live journeys and both independent reviews passed, final complete local gate passed24infra/467API/22frontend plus lint/type/build.
- [x] User explicitly authorized fictional policy PDF uploads for default-delete/Keep tests in the existing consenting chat; actual default-delete, Keep/copy, owner deletion and revoked-copy factory checks passed; no visible post-delete toast claim is made.
- [x] Astra task brief and local acceptance agreed; local blockers satisfied. The user approved pre-upload default-delete/Keep retention semantics and the local Must gate passed; actual implementation/integration evidence and final24infra/467API/22frontend gate passed. Separately deferred external limits remain explicit.
- [x] Sol implementation for this task is frozen within the shared Task18/19 boundary.
- [x] Final local checks passed24infra/467API/22frontend, zero skips, plus lint/type/build; results captured in tasks-18-19-verification.md.
- [x] Astra inspected files/results, returned defects, and rechecked corrections. Exact RED/GREEN evidence is recorded in tasks-18-19-verification.md.
- [x] Matt Standards review completed; final recheck0 remaining at manifest83b211c12eb41fe7c7f62ea7f25ad8d832a966c702fff39e3aecebd2f9b68af4.
- [x] Matt Spec review completed; final recheck0 remaining at the same frozen snapshot.
- [x] Local acceptance met and evidence recorded at1646ebc/PR29; hosting remains explicitly deferred.
- [x] Technical prerequisites for dependent local work met; native wording/offline-phone/hosting limits remain recorded. Root released Tasks20–22 execution from1646ebc.

### Task 20 — Waste sorting

**Current status: locally accepted.** Final25infra/629API/33frontend gate, independent Standards0/Spec0 and primary runtime/browser proof passed. See tasks-20-22-verification.md. Detailed checkpoint bullets below are historical; their then-pending review/gate statements are superseded by this acceptance.

- [x] Frontend candidate frozen:28 tests, TypeScript and lint passed; Astra inspected the typed public/report boundaries. Root subsequently completed integrated browser/PDF checks, recorded below. The earlier actual Firestore batch produced6 passes and1 meaningful failure: a newer unavailable assessment left the old donation/current waste actionable. Correction then passed all7 actual Firestore cases in2.42s: old donation denied, newest unknown scope excluded from known totals, historical facts retained. The final owner/prompt guard then showed isolated prior-behavior RED4 failures/1 pass and current GREEN32 pure cases; Astra independently ran13 public-webhook/contract cases successfully. All eight catalogs now have exactly eight new waste keys with existing values unchanged; seven bounded configured-Flash translation calls passed. Final pure34 cases passed. Root frozen-UI desktop/mobile/available-empty-unavailable checks passed; actual integrated service/PDF subsequently passed as recorded below; full gate and independent final reviews were pending at this historical checkpoint; no acceptance claim.

- [x] Astra dispatched original Sol recovery for model/report/persistence integration from1646ebc after reading issue21 body/comments. Shared backend ownership is exclusive to this lane initially. Initial eligibility/street consistency checks observed3 failures, then11 passing pure cases. Wire/DTO checks now24passing; four actual Firestore integration cases passed1.80s with exact cleanup. Initial malformed-test-baseline failures are not counted as behavioral RED. Root actualPro exposed contradictory contaminated salvage; conservative fallback retained valid loss. Corrected actualPro rerun passed with discard/discard/recycle, unchanged baseline/original hash and no inline bytes in persisted trace; model valuation changed268→316, not an accuracy or determinism claim. Subsequent integrated evidence is recorded below; final combined acceptance was pending at this historical checkpoint.

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Loss report provides item disposal categories and aggregate estimated cleanup volumes.

- [x] Astra prepared concrete disjoint pure-domain execution and later integration ownership in tasks-20-22-execution.md. Three restored pure-domain source/test files and their separate note have eight prior focused tests; integration and independent review were pending at this historical checkpoint, with no Task20 acceptance claimed.

- [x] Preparatory file/interface/test brief written in tasks-18-22-brief.md; source and current modules inspected. Planning only.
- [x] Astra task brief, explicit product choices and local prerequisites satisfied; implementation and final local acceptance passed.
- [x] Implementation and Astra corrections frozen; focused, operational and final combined gate/review results passed.
- [x] Relevant focused, operational and final local checks run; exact results recorded.
- [x] Astra inspected source/results and corrected/rechecked all actionable findings.
- [x] Matt Standards independent final review and supplements returned0 outstanding findings.
- [x] Matt Spec independent final review and supplements returned0 outstanding findings.
- [x] Local acceptance met with recorded evidence. Hosting/cloud acceptance remains explicitly deferred; no deployment claim.
- [x] Local technical prerequisites met; remaining real-world/submission limits recorded separately.

- [x] Integrated actual-Pro capture exposed omitted unaffected waste rows: six valid loss items but only four affected waste entries. Exact captured-wire regression failed before canonical ok/null-quantity normalization and then passed; Astra independently replayed the unchanged captured loss and ran five comparison cases. The original unavailable report is retained. Root fresh captured-output replay through actual local service clients passed in12.911s: six baseline/loss/waste rows, unchanged baseline, worker denial, upload dedupe, protected report denial, three original hashes/ledger rows and synthetic Unassigned aggregate. This was captured actual-Vertex output replay, not a new model call. A media-ID-versus-SHA harness failure was corrected without app changes. Actual handler→Firestore street flow also passed with virtual Telegram: owner confirmation, worker denial, duplicate stability and old-intent replay could not revert a newer label. Root actual native four-page PDF then passed: all three full hashes exactly once, bytes/limits/synthetic label/waste/fixed food rule present, capability absent from text/links; all pages visually inspected. Native UI stall resolved after user unlock, without an application change. Full gate/final review were pending at this historical checkpoint.

### Task 21 — /check

**Current status: locally accepted.** Final25infra/629API/33frontend gate, independent Standards0/Spec0 and primary runtime/browser proof passed. See tasks-20-22-verification.md. Detailed checkpoint bullets below are historical; their then-pending review/gate statements are superseded by this acceptance.

- [x] Astra dispatched original Sol task1 for disjoint public-check domain/projection/intent modules from1646ebc after reading issue22 body/comments. Initial pure/reader tests15passed and actual Firestore intent test1passed; duplicate-age reader correction reviewed. Shared routing/catalog integration received its explicit handoff. The initial Task21 domain files are frozen; root actual official-HTTP/local-Firestore reader probe passed with degraded JPS/MET, no nearby reports and two public destinations, without private identities. Shared handler integration is frozen and its actual local probe passed below. New constrained ADK selector passed two independent in-memory runner tests; root actual configured-Flash probe then returned check_summary_partial/source=model with six persisted ADK documents and recursive privacy checks passed. Inputs were captured actual official-source/local-store facts for a synthetic query location. That earlier checkpoint did not claim full Task21 acceptance; final acceptance is recorded above.

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Any user shares a location to view current nearby warnings and listed destinations.

- [x] Preparatory file/interface/test brief written in tasks-18-22-brief.md; source and current modules inspected. Planning only.
- [x] Astra task brief, explicit product choices and local prerequisites satisfied; implementation and final local acceptance passed.
- [x] Implementation and Astra corrections frozen; focused, operational and final combined gate/review results passed.
- [x] Relevant focused, operational and final local checks run; exact results recorded.
- [x] Astra inspected source/results and corrected/rechecked all actionable findings.
- [x] Matt Standards independent final review and supplements returned0 outstanding findings.
- [x] Matt Spec independent final review and supplements returned0 outstanding findings.
- [x] Local acceptance met with recorded evidence. Hosting/cloud acceptance remains explicitly deferred; no deployment claim.
- [x] Local technical prerequisites met; remaining real-world/submission limits recorded separately.

- [x] Shared Task21 integration tests passed19 pure cases with two actual-Firestore cases skipped in that pure run. The separate granted SDK window then passed both real-store intent/HTTP cases in4.91s: sender/locale/original-message binding, concurrent claim, sanitized cache replay, late pre-send failure, new intent preservation and no unregistered shop creation; exact isolated collections were removed. Non-English fallback/overflow corrections, translations and the complete-handler operational check subsequently passed, as recorded below.

- [x] Final Task21 source recheck: Astra independently passed41 projection/reader/service/webhook/ADK/i18n tests in4.71s (two dependency warnings). Baseline1646 comparison found zero changes to existing catalog values in all eight languages, with29 new check keys each and all non-English review flags stillfalse. Actual complete-handler operational evidence subsequently passed below; final combined review/gate were pending at this historical checkpoint.

- [x] Root frozen whole-handler Task21 probe exited0 using actual isolated Firestore and virtual Telegram: no signup/shop creation, submitted precise point absent from stored intent/cache, duplicate update caused no resend,30-second gate/five-minute expiry held, and two captured-source reads were labelled as replay rather than fresh external/model calls. Exact collections were removed. The first harness privacy assertion used the same coordinate as a lawful public destination; moving the synthetic query resolved that harness-only failure without app changes. Translation batch completed seven bounded configured-Flash calls for29 keys each; prior176 non-English values remained unchanged. Final combined gate and independent reviews subsequently passed, as recorded above.

### Task 22 — Learning loop

**Current status: locally accepted.** Final25infra/629API/33frontend gate, independent Standards0/Spec0 and primary runtime/browser proof passed. See tasks-20-22-verification.md. Detailed checkpoint bullets below are historical; their then-pending review/gate statements are superseded by this acceptance.

- [x] Astra dispatched original Sol task1 for disjoint pure outcome/calibration models and tests using task-22-integration-brief.md after the Task20 frontend handoff. No shared hooks, SDK, runtime or feature acceptance is implied.

- [x] Task22 persisted RadiusPlan guard observed malformed applied official-Danger input accepted before correction, then rejected; arithmetic, realm, policy and version bindings are now enforced. Astra independently ran18 pure/domain/fake-transaction cases successfully in0.63s. The bounded prompt/token store and public trend DTO then froze with22 pure/fake cases passing; Astra independently ran29 combined service/domain/store cases in1.29s. Root actual store concurrency subsequently passed below; shared integration/operational acceptance were pending at this historical checkpoint. Source R3 was checked: due time is accepted alert plus six hours OR immediate explicit closure, not six more hours after closure.

Scope: Should — full local Must acceptance required; hosting deferred. Deliverable: Owner feedback produces transparent outcome metrics and constrained area calibration.

- [x] Preparatory file/interface/test brief written in tasks-18-22-brief.md; source and current modules inspected. Planning only.
- [x] Astra task brief, explicit product choices and local prerequisites satisfied; implementation and final local acceptance passed.
- [x] Implementation complete; Astra personally completed the later authorized corrections and UI work.
- [x] Relevant focused, operational and final local checks run; exact results recorded.
- [x] Astra inspected source/results and corrected/rechecked all actionable findings.
- [x] Matt Standards independent final review and supplements returned0 outstanding findings.
- [x] Matt Spec independent final review and supplements returned0 outstanding findings.
- [x] Local acceptance met with recorded evidence. Hosting/cloud acceptance remains explicitly deferred; no deployment claim.
- [x] Local technical prerequisites met; remaining real-world/submission limits recorded separately.

- [x] Root frozen Task22 store probe used actual Firestore and exited0: concurrent owner replies converged on one immutable response/fact; worker denied; final Danger deferred; expired sending became uncertain without resend; virtual prompt did not authorize an accepted-message callback; five persisted synthetic-fixture responses shrank the multiplier to0.9 once, a confirmed inside/no-earlier-alert report grew it to0.99 once, and old generation was denied. Exact isolated collections were cleaned. This verifies store behavior; shared jobs/dispatch/analytics/public endpoint/UI were pending at this historical checkpoint.

### User-requested dashboard design refinement (Tasks20–22)

- [x] Explicit user visual amendment recorded; Astra read frontend-design skill and web/AGENTS.md and wrote dashboard-polish-plan.md with palette/type/layout and brief-specific critique.
- [x] Exclusive frontend handoff released after Task22 backend contract freeze; Sol recorded the map/activity/compact strip/feedback trend plan, preserving locally bundled Source Sans 3 and dashboard-scoped CSS.
- [x] Frontend implementation and Task22 panel frozen for root verification: map/activity hierarchy, compact action strip, responsive recovery/feedback, exact public proxy and strict DTO. TypeScript/lint passed;31 prior complete frontend tests plus five final focused cases passed (not a claimed combined final total). Seeded-history accepted-alert wording observed RED and corrected with a formatter regression. Root build/browser checks were pending at this historical checkpoint.
- [x] Root frozen frontend gate exited0:33 frontend tests, zero skips, lint/type checks and production build. Test delta22→33 is six Task20 cases plus five Task22 feedback cases.
- [x] Root actual desktop review prompted a compact-first-screen correction; map now begins at454px with about317px visible at1512×771, composition accepted.390px and320px have no page overflow; empty/unavailable states preserve unknown values. Actual cleanup-table keyboard and marker labelling gaps were returned to Sol. A subsequent real Space-key test exposed marker focus/popup loss on selection redraw; correction and final keyboard/refresh verification were open at this historical checkpoint.
- [x] Root actual desktop/tablet/390px/320px keyboard/focus/overflow/state verification passed on final dashboard build. Marker and event-circle popups retain close-control focus across data polling; removed focused objects fall back to the map, while outside input focus stays untouched. All map controls are44px, labelled tables scroll from the keyboard, no dashboard animation/transition was present, and report/print styles remain unchanged.
- [x] Astra corrections and independent final reviews resolved; actual responsive/keyboard/browser verification passed, with controlled tile-failure injection separately unperformed.

- [x] Task22 shared integration checkpoint: reference-basis and Watch-history guards passed24 pure/domain/fake-store cases; observed Watch RED was corrected so earlier Watch acceptance blocks false missed-alert growth but cannot trigger six-hour prompts or shrink calibration. Atomic episode-history helper and risk transaction boundary passed three RED→GREEN cases for first reporter episode/explicit closure, legacy start refusal and rollback. Recovery Sol owns history/service/shared hooks; the other Sol owns only outcome analytics/tests and additive nullable schema fields. Actual integrated SDK/job acceptance was pending at this historical checkpoint.
- [x] Root responsive checks additionally passed a320px189-character unbroken shop name without page overflow, explicit available/empty/unavailable coverage, and keyboard ArrowRight scrolling of the cleanup table with visible3px focus outline. Semantic text contrast measured4.55–12.27. The one-file marker/popup focus correction was source-reviewed and passed TypeScript/lint; actual post-correction keyboard/refresh checks were pending at this historical checkpoint.

- [x] Astra independently inspected the current atomic-history and outcome/calibration chain and ran27 pure/fake-transaction cases:27 passed in0.80s, exit0. Root actual marker keyboard checks then passed Space selection, changed-data polling, close-control focus, removed-shop map fallback and preservation of outside-input focus. The adjacent event-circle popup branch was still being corrected at this historical checkpoint before final all-popup verification.

- [x] Disjoint Task22 analytics source/schema reviewed: Astra independently passed11 fake-client cases in0.76s. Unrelated same-generation area leakage was observed RED and corrected; history truncation, unavailable analytics and immutable reference attribution are covered. Eight nullable outcomes fields are proposed, with no new calibration table. Root actual analytics SDK probe is pending. Shared service/domain/history pure suite reached33 cases; final integration remains open.

- [x] Task22 local synthetic-history helper is written and source-reviewed; Astra seed/analytics16 cases passed in0.55s. It plans six distinct historical episodes of one owned synthetic shop, with explicit fixture provenance and replay-stable facts, not six independent shops or real Telegram acceptance. Actual seed/job verification was pending at this historical checkpoint; adapter reset isolation and bounded in-flight history corrections are in progress.

- [x] Root actual isolated Firestore/BigQuery analytics probe passed: five responses over six episodes, one unknown, five fixture responses/zero real acceptances,0.9 calibration/history, unavailable missing analytics, physical duplicate dedupe, generation/privacy and exact query cleanup. The persistent9050 emulator stalled without OOM; identical module passed against a fresh same-version9052 instance, so no product analytics correction is claimed. Persistent runtime recovery remains root-owned.
- [x] Task22 translations completed seven bounded configured-Flash calls for eight keys per language. Astra independently compared all eight catalogs with1646ebc: zero existing values changed,45 new keys each (8 waste+29 check+8 outcome); actual i18n suite10 passed in1.49s. Non-English translations remain unreviewed.

## Latest Astra-led UI and submission audit

- [x] Read actual dashboard/report sources, retained desktop screens, teammate context, installed Next client guidance and primary research; record plan/critique and challenge evidence in ui-and-winning-audit.md and ui-primary-research.md.
- [x] User confirmed portal GGSI challenge and Astra ownership; preserved local-only/no-CI/hosting-deferred scope.
- [x] Task22 root integrated actual FS/BQ/app-route/seed probe passed24.314s: replay/calibration, protected job, owner/worker, first-response/outage recovery, synthetic-only projection and generation reset. Telegram edge remained in-process fake.
- [x] Narrow local outcomes migration has seven fake-client checks; actual emulator schema patch failed new-column query as expected, root instead verified a separate highground_v3 copy of all five table row multisets/hashes, new-column queryability and unchanged original dataset, then switched only ignored local BQ_DATASET. No false metadata-only migration success.
- [x] Astra implemented scoped selected-shop drill handoff, direct demo navigation, explanatory existing simulation controls, tile loading/error/retry feedback and labelled keyboard report-table regions. No new dependencies, flood features or data claims.
- [x] Root browser review of the new UI passed selected-shop → drill → location handoff, desktop/tablet/320/390px navigation without overflow,46px action buttons and both report-table keyboard scrolling regions with visible focus. Actual basemap loaded15 tiles; report print styles stayed unchanged. Evidence: task20-22-acceptance/ui/drill-ui-proof.json.
- [ ] Controlled tile-network failure/retry injection remains a separate unperformed robustness check; the retained grey screenshot was not evidence of a live tile failure.
- [x] Final local gate/reviews against1646ebc include intended untracked20–22 files and the UI amendment:25infra,629API,33frontend,lint/type/build passed; both independent axes0. Earlier621-case checkpoint and subsequent runtime corrections are retained below as historical evidence, not confused with final acceptance.

### Final Tasks20–22 correction checkpoint

- [x] Astra corrected the visible outcome episode reference with two observed RED→GREEN prompt cases, extracted a typed shared reply guard while preserving existing Danger/policy/recovery behavior, and moved outcome fact/calibration reads and exact acknowledgments behind typed store operations. The stale ADK assertion now checks rejection of the unsupported slash-combined condition through the actual response schema. Focused pure checks passed107 cases;21 emulator cases were explicitly skipped in the second pure batch, not claimed as integration acceptance.
- [x] Seven bounded configured-Flash calls translated only two new episode-reference keys; all prior catalog values and fixed Danger text remained unchanged. Current catalogs have47 new keys versus1646ebc; non-English review flags remain false.
- [x] Independent Matt Standards and Spec rechecks against coherent frozen v2 each returned0 outstanding findings. Both separately reviewed the subsequent single-line BigQuery emulator tuning and again returned0. Their reviews were read-only; full local verification is a separate gate.
- [x] Root A/B evidence: unchanged hard768MiB/image/persistent-data settings with soft512MiB/GOGC100 passed25 focused actual integration tests in76.11s, where soft256MiB/GOGC50 had stalled. Only the runner environment pair changed; no Docker VM increase, production setting, data replacement or timeout increase. Root then passed the reviewed-source actual Task22 journey in32.07s on primary9050. This supports the local tuning, not a claim of permanent emulator reliability.
- [x] Final combined gate on the reviewed correction exited0:24infra9.495s;621API/no skips/six dependency warnings200.79s;33frontend/no skips, lint/typecheck/production build passed. See tasks-20-22-verification.md.
- [x] Historical runtime blocker resolved: sequential retained-catalog slowness and fresh concurrent-query OOM were separated, then exact SQL-copy preservation plus bounded emulator-only query serialization passed actual primary requests and browser polling. Original data/history remain retained.
- [x] Executed isolated model-unavailable drill: actual dispatch/composer with in-process fake store/sinks/Telegram, Warning selector failure falls back; Danger invokes no selector, emits exact fixed simulation message and has no property actions/buttons. Coherent offline card rendered from the retained six-item synthetic recovery baseline, four ranked displayed items/RM850; no new model call, Telegram send or phone-airplane-mode claim. See single-shop-drill-runbook.md for artifact boundaries.

- [x] Historical incomplete-copy diagnostic resolved: list_rows proof was invalidated (alerts2vs28,outcomes0vs6); subsequent SQL enumeration preserved exact8/28/3/13/6 counts/schema/row hashes in the adopted live volume. No incomplete copy was adopted.

- [x] Root exact SQL-copy diagnostic preserved8/28/3/13/6 business rows/schema and unchanged source. Fresh-clone sequential requests were subsecond, but parallel round2 caused an observed768MiB OOM. Astra personally added an endpoint-validated emulator-only bounded in-process query/result/cleanup lock; four meaningful RED cases became GREEN. Helper19 passed; helper+outcome30 passed/one real-SDK deselected. Eight new cases make next full API total629.
- [x] Actual locked parallel-runtime replay, final629-case API gate and both independent correction rechecks passed. Cloud requests and existing SDK/proxy deadlines are unchanged; other local processes still require coordination.

- [x] Root locked-clone real endpoints passed two sequential requests and three concurrent pairs, all available0.46–1.19s. Exact SQL-copy business counts/schema/hashes and original preservation passed. Both independent query-lock reviews returned0; cloud behavior/deadlines unchanged.
- [x] Final runner volume adoption retained historical-data protection: reviewers found the recovered-volume guard omission, Astra observed the orphaned-volume fake-Docker regression RED→GREEN, and all9 lifecycle cases/4subtests passed. One added case makes25infra; finalAPI629/frontend33 unchanged. Root reruns affectedinfra separately because its full gate had already passed the older24 before this narrowfix.
- [x] Final629API/33frontend gate,25infra rerun and both lifecycle rechecks recorded; local milestone accepted.

### Final local Tasks20–22 acceptance

- [x] Full-gate-v3 exited0:629API/no skips80.09s;33frontend/no skips;lint/typecheck/production build passed. The final infra-only retained-volume correction was verified separately:25passed10.318s. API629=467+42+36+69+7+8;infra25=24+1.
- [x] Both original independent Matt reviewers returned0 after query-lock and retained-volume supplements. Source is frozen for root commit-byte verification; no Git writes by Astra.
- [x] Final actual primary8000 returned eight available reads1.01–5.57s with six responses preserved. Chrome3001 displayed six synthetic shops,RM472 reported lifted,one vehicle,one real API acceptance,five virtual alerts,six seeded responses and0.99/version2; official unavailable status remained explicit.
- [x] Local Tasks20–22 accepted. Prior diagnostic/then-pending bullets above are historical and superseded by this final checkpoint. Hosting/cloud acceptance,native-language human review,real-shop validation,second physical tester,phone airplane-mode test,controlled tile-failure injection and final recorded video/deck/submission remain outside this local completion claim.

- [ ] Hosted deployment/cloud acceptance remains deferred; local completion does not tick this external gate.
