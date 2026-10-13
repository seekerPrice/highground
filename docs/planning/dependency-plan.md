# Active implementation dependency plan

Current reviewed application: `5be7f1800becf3671c5ba2ff66e5a380e3b0a277`. The user authorizes all Tasks1–22 by actual dependencies, with parallel disjoint work and no calendar waits. **The complete local Must gate is now accepted: native PDF verification, recovered-runtime full gate and independent print correction reviews passed. Should implementation may begin by dependency.** Hosting remains deferred, as do separately tracked second-phone and real Telegram media-upload acceptance. Should implementation may now proceed by dependency. Stretch is pitch-only; no CI or repository-connected automation.

## Current dependencies and evidence

| Task | Technical prerequisites | Current local state / remaining boundary |
|---|---|---|
| 1 scaffold | none | Accepted/reviewed |
| 2 infrastructure | 1 | Scripts and local verification/review passed; actual cloud provisioning deferred |
| 3 data clients | 1 | Accepted/reviewed; live source freshness and timezone limits explicit |
| 4 Telegram webhook | 1 | Accepted/reviewed; actual local callback passed |
| 5 onboarding/i18n | 4,6; configured storage | Accepted/reviewed; consenting own-chat registration passed; native translation review separate |
| 6 ADK/session foundation | 1 | Actual Firestore sessions/configured Vertex calls and review passed |
| 7 alert dispatch | 3,5,6; event sinks | Accepted/reviewed; actual Warning and fixed Danger paths |
| 8 destinations/vehicles | 7 | Accepted/reviewed; historical source labels and actual duplicate-safe callback |
| 9 evidence/neighbour reports | 5,6,7; media sinks | Local integrated acceptance/review passed; actual Telegram photo upload permission pending |
| 10 escalation/polling | 3,7,8,9 | Accepted/reviewed; actual local polling; hosted OIDC/Scheduler deferred |
| 11 inventory/lift-first | 5,6,7,9 | Accepted/reviewed with actual Pro and service journey; valuations remain estimates |
| 12 recovery reports | 9,11 | Accepted/reviewed; actual Pro, protected evidence and immutable baseline |
| 13 report page | 12 | Production privacy/mobile/keyboard/failure states passed; native PDF/print accepted and correction reviewed |
| 14 packaging/deploy | 2 plus stable API/web contracts | Local non-root image/runtime checks and reviews passed; deployment deferred |
| 15 dashboard | 7,8,9,11;16 reset contract | Local acceptance/review passed including actual operator reset/retry and metrics |
| 16 reproducible demo | stable14 packaging and15/dispatch interfaces | Actual six-shop/three-vehicle seed, virtual journey, consenting-owner binding and duplicate-safe actions passed; redeploy deferred |
| 17 hardening | completed component gates across1–16 | Full local test/review and factory/manual recovery passed; complete local Must gate accepted |
| 18 offline card | full local Must;11 inventory,8 destinations,7 delivery | Brief prepared only; no implementation; font/shaping/photo-transport probes required |
| 19 policy check | full local Must;9 ingestion,11 inventory | Brief prepared; pre-upload retention/Keep-copy policy approved; PDF/deletion SDK probes required |
| 20 waste sorting | full local Must;12/13 report,15 map/metrics | Brief prepared; street/deduplication/donation semantics explicitly approved |
| 21 public check | full local Must;3 current sources,8 destinations,9 attributed reports | Brief prepared; privacy/TTL/rate explicitly approved; current geographic reader remains implementation work |
| 22 learning loop | full local Must;7/10 episodes,15 metrics | Brief prepared; outcome/coverage/window/calibration rules explicitly approved |

Source Should priority18→19→20→21→22 governs limited capacity, not artificial serial blocking. None inherently requires the preceding Should. Detailed proposed files, interfaces, tests and approved product choices are in [tasks18–22 brief](tasks-18-22-brief.md). Explicit approvals are recorded in approved-decisions.md; publication alone does not approve further amendments.

## Reviewed checkpoint and local gate closure

The corrected `./infra/test.sh` atf6efd315 exited0:24 infrastructure,339 API tests (no skips; five dependency warnings),19 frontend tests (no skips), lint/type checks/production build. Independent final Standards0/Spec0 rechecks resolved fixture ownership/Danger routing and obsolete-event history recovery defects. API and web images were actually built/smoke-tested; the API was rebuilt after the correction.

Root's actual shared factory/manual recovery, six-virtual Warning/Danger/reset, lost-response/superseded/new-intent retry and consenting-owner vehicle/stock confirmations passed. Duplicate taps retained exactly two facts, one real acceptance, one reported vehicle and RM472 displayed/confirmed synthetic stock; remaining five recipients were virtual. See [operational verification](task-17-operational-verification.md). These observations are not real-shop valuation, independent physical-action or second-phone evidence.

At5be7f18, the corrected native two-page A4 PDF contains all three hashes exactly once and all byte counts, with capability absent and readable pagination. The recovered-runtime full gate passed24 infrastructure/339 API/19 frontend tests, no skips, plus lint/type/build. Both independent print reviews returned0 findings. Three actual factory dashboard reads returned200 with six shops and kept dataset count4→4. Local Must acceptance is complete; see UI and operational verification for the prior failures/recovery evidence. Hosted resources, production IAM, live fresh official flood coverage, native translation review and real-world accuracy are separate explicit limitations, not grounds to invent successful acceptance.

## Ownership after the gate

Astra owns briefs/checklists and actual review/correction coordination. Root owns Git/GitHub, runtime restarts, real Telegram/browser operations and consent, emulator SDK windows and deployment authority. Astra has dispatched Task18 card and Task19 policy domain lanes; shared entrypoints and dependency changes initially belong only to the Task18 lane, with an explicit handoff before policy integration.

After this accepted checkpoint, two Sol lanes may work disjoint new domain/agent/test modules. A single integration owner at a time controls `api/telegram_webhook.py`, `api/main.py`, media/retention schemas, i18n, config/env/README and dependency pins. One frontend owner controls DTOs/components/fixtures and the frontend lockfile. Freeze typed API contracts before handing them to the UI lane; serialize report/dashboard amendments from19/20/22. Calibrated triage changes cannot race another dispatch/radius integration.

Each implementation slice gets focused checks, observed RED/GREEN for new guards, Astra source/correction review and separate independent Matt Standards/Spec reviews against a pinned committed baseline. Record implemented, locally accepted, provisioned and deployed separately. A common local gate may cover multiple stable slices but never conceals their individual acceptance gaps. Upcoming execution uses the latest parent-pinned documentation checkpoint with unchanged reviewed application as its baseline.
