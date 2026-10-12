# Active implementation dependency plan

Latest authorization: implement all Tasks 1–22 without individual Task N waits; parallelize disjoint work. Task numbers remain traceable to the preserved source. No calendar waiting; all safety, stack and no-CI rules remain. Latest local-first amendment: Should implementation begins only after the entire Must journey is verified locally. Cloud provisioning/deployed acceptance remain pending until hosting. Stretch remains pitch-only.

## Technical prerequisites

| Task | Depends on | Current dispatch or boundary |
|---|---|---|
| 1 scaffold | none | Complete and reviewed |
| 2 infrastructure | 1 | Script/local verification and review passed; actual cloud provisioning deferred |
| 3 data clients | 1 | Implemented and reviewed; stale upstream coverage remains explicit |
| 4 Telegram webhook | 1 | Implemented/reviewed; real local callback passed |
| 5 onboarding/i18n | 2, 4 | Implemented with actual Firestore and live owner registration; both review axes passed (8818a93) |
| 6 ADK skeleton | 1 | Implemented/reviewed with actual Firestore sessions and configured Vertex calls |
| 7 alert dispatch | 2, 3, 5, 6 | Implemented with deterministic safety and durable delivery; both review axes passed (8818a93) |
| 8 destinations/vehicles | 7 | Sourced places can be prepared earlier; exact actions built on dispatch |
| 9 media/neighbour reports | 2, 5, 6, 7 | Shared ingestion then photo report pipeline |
| 10 escalation/polling | 3, 7, 8, 9 | OIDC and fixed Danger paths integration |
| 11 inventory/lift-first | 5, 6, 7, 9 | Ingestion reused; confirmation snapshots match displayed list |
| 12 loss reports | 11 | Baseline then after-video comparison |
| 13 report page | 12 | Web lane; unguessable report access/private media |
| 14 deployment | 2, 10, 11, 12, 13 | Prepare packaging and local container checks; hosted acceptance deferred by user |
| 15 dashboard | 7, 8, 9, 11 | Web lane can parallel report/deployment work after API contracts stabilize |
| 16 seeded demo/redeploy | 14, 15 | Seed/verify locally with real consenting accounts and virtual shops; redeploy deferred |
| 17 hardening | 16 | Failures tested throughout; final integration acceptance across 1–17 here |
| 18 offline card | 17 | Local Must gate required; cloud acceptance pending |
| 19 policy check | 17 | Local Must gate required; cloud acceptance pending; retention exception explicit |
| 20 waste sorting | 17 | Local Must gate required; cloud acceptance pending; report contract already delivered by 12–13 |
| 21 public check | 17 | Local Must gate required; cloud acceptance pending; warning/geo contracts already delivered |
| 22 learning loop | 17 | Local Must gate required; cloud acceptance pending; calibrated rules cannot suppress official Danger |

Should numbering sets prioritization when capacity is limited, not an artificial serial blocker under the latest parallel-work authorization.

Some listed dependencies gate full acceptance, not all preparatory coding. Do not claim provisioned/deployed/live status from local stubs or fixtures. Task 2 cloud verification remains open until hosting/resource provisioning is authorized, even after root establishes the target project/billing.

## Shared-file ownership

Astra owns planning/checklists/AGENTS and coordinates review/corrections. Root owns GitHub mutations and final commits. Each Sol lane owns its assigned files; only one lane may change api/main.py, backend dependency locks, root env example, README or frontend dependency locks at a time. Require coordination before extending a shared model.

Initial lanes: infrastructure owns infra/setup.sh and schema/config/test assets under infra plus .env.example additions if necessary; data owns api/models.py, api/tools/datagov.py, data fixtures/tests and docs/planning/data-source-research.md. Neither modifies api/main.py or backend locks without Astra approval.

Current milestone: Task 10 lane owns polling, active-risk/episode state, Scheduler authentication, main/dispatch and settings. Task 11 lane owns video/inventory/loss-agent work, webhook/onboarding/composer and backend dependency changes. Agree shared risk interfaces and serialize any cross-lane edits before changing them. Details are in tasks-10-11-brief.md.

## Review gates

Record local implementation/acceptance separately from deferred provisioning and deployment. Never keep local Should work artificially blocked on a cloud action the user explicitly deferred, once the full local Must gate has passed.

Approved local test scope: six explicitly synthetic shops, the consenting own-chat and virtual recipients. Keep actual second-phone and hosted acceptance pending separately; do not describe virtual sends as real-neighbour Telegram delivery. See approved-decisions.md for the recorded decision window.

Baseline for the Tasks 2/3/4/6 foundation: 142178f. Candidate: 9df978d. Each lane runs focused local checks and sends concrete failures to Astra. Astra inspects files/results, directs corrections, and rechecks affected behaviour. Candidate commits receive independent Matt Standards/Spec review when execution agents release slots. Missing external credentials never count as successful external verification; continue other unblocked work while root resolves facts.

The foundation and privacy correction passed both axes in final commit 4666575. That commit is the Tasks 5/7 review baseline; final candidate 8818a93 passed both Matt axes after the distance correction. Local synthetic fixtures do not substitute for native translation review, two consenting phone testers, real-shop valuation accuracy or production IAM checks.

Tasks 8/9 dispatched from reviewed code baseline 8818a93; subsequent documentation-only commits do not change that implementation comparison.

Tasks 8/9 implementation was reviewed through 1a4d7b1 with zero outstanding findings on both axes and a final complete local gate (6 infrastructure + 175 API tests, no skips, frontend checks passed). Task 8 live own-chat acceptance passed; Task 9 live photo upload remains explicitly pending consent. Tasks 10/11 are now dispatched in parallel from that code baseline.
