# Active implementation dependency plan

Latest authorization: implement all Tasks 1–22 without individual Task N waits; parallelize disjoint work. Task numbers remain traceable to the preserved source. No calendar waiting; all safety, stack and no-CI rules remain. Latest local-first amendment: Should implementation begins only after the entire Must journey is verified locally. Cloud provisioning/deployed acceptance remain pending until hosting. Stretch remains pitch-only.

## Technical prerequisites

| Task | Depends on | Current dispatch or boundary |
|---|---|---|
| 1 scaffold | none | Complete and reviewed |
| 2 infrastructure | 1 | Sol infrastructure lane; script/local verification can proceed before project facts |
| 3 data clients | 1 | Sol data lane; independent of cloud provisioning |
| 4 Telegram webhook | 1 | Next backend slice; live acceptance needs bot/tunnel credentials |
| 5 onboarding/i18n | 2, 4 | Persistence needs cloud connection; local logic and committed templates can be built first |
| 6 ADK skeleton | 1 | Can run independently after backend package ownership is assigned |
| 7 alert dispatch | 2, 3, 5, 6 | Deterministic safety and event/recipient idempotency required |
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

## Review gates

Record local implementation/acceptance separately from deferred provisioning and deployment. Never keep local Should work artificially blocked on a cloud action the user explicitly deferred, once the full local Must gate has passed.

Baseline for Tasks 2/3: 142178f. Each lane runs focused local checks and sends concrete failures to Astra. Astra inspects files/results, directs corrections, and rechecks affected behaviour. Candidate commits receive independent Matt Standards/Spec review when execution agents release slots. Missing external credentials never count as successful external verification; continue other unblocked work while root resolves facts.
