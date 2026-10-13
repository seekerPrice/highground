# Active implementation dependency plan

Accepted local Must application: `5be7f1800becf3671c5ba2ff66e5a380e3b0a277`; Tasks18/19 are locally accepted and independently reviewed at1646ebca0fadae7afd5c50b4b189ecdac12426be, with final24infra/467API/22frontend gate passed. Tasks20–22 implementation, operational probes and independent Standards0/Spec0 reviews are complete. The post-gate local emulator failure was corrected and independently rechecked; actual locked-clone sequential/parallel calls passed. Final25infra/629API/33frontend verification and actual primary runtime/browser checks passed; Tasks20–22 are locally accepted. See tasks-20-22-verification.md. The user authorizes all Tasks1–22 by actual dependencies, with parallel disjoint work and no calendar waits. **The complete local Must gate is now accepted: native PDF verification, recovered-runtime full gate and independent print correction reviews passed. Authorized Should implementation has also completed its local gates.** Hosting and separately tracked second-phone/real-shop media acceptance remain deferred. Explicitly synthetic Task18/19 Telegram media was separately authorized and tested. Stretch is pitch-only; no CI or repository-connected automation.

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
| 18 offline card | full local Must;11 inventory,8 destinations,7 delivery | Locally accepted/reviewed; host/Linux rendering, actual consenting-chat downloaded image and final full gate passed; native wording/offline-phone/hosting limits explicit |
| 19 policy check | full local Must;9 ingestion,11 inventory | Locally accepted/reviewed; actual configured Pro, default-delete/Keep/copy/delete, trace privacy, private/public UI and final full gate passed; real-policy/provider-retention/hosting limits explicit |
| 20 waste sorting | full local Must;12/13 report,15 map/metrics | Actual Pro/captured-output journey, owner/street guards, browser/PDF, full gate and independent review passed; locally accepted after corrected primary-runtime/browser confirmation |
| 21 public check | full local Must;3 current sources,8 destinations,9 attributed reports | Complete handler/actual-source/configured-Flash probes, full gate and independent review passed; locally accepted after corrected primary-runtime/browser confirmation |
| 22 learning loop | full local Must;7/10 episodes,15 metrics | Actual integrated route/seed/analytics, responsive UI, full gate and independent review passed; locally accepted after bounded local query correction, exact data migration and primary-runtime/browser confirmation |

Source Should priority18→19→20→21→22 governs limited capacity, not artificial serial blocking. None inherently requires the preceding Should. Detailed proposed files, interfaces, tests and approved product choices are in [tasks18–22 brief](tasks-18-22-brief.md). Explicit approvals are recorded in approved-decisions.md; publication alone does not approve further amendments.

## Reviewed checkpoint and local gate closure

The corrected `./infra/test.sh` atf6efd315 exited0:24 infrastructure,339 API tests (no skips; five dependency warnings),19 frontend tests (no skips), lint/type checks/production build. Independent final Standards0/Spec0 rechecks resolved fixture ownership/Danger routing and obsolete-event history recovery defects. API and web images were actually built/smoke-tested; the API was rebuilt after the correction.

Root's actual shared factory/manual recovery, six-virtual Warning/Danger/reset, lost-response/superseded/new-intent retry and consenting-owner vehicle/stock confirmations passed. Duplicate taps retained exactly two facts, one real acceptance, one reported vehicle and RM472 displayed/confirmed synthetic stock; remaining five recipients were virtual. See [operational verification](task-17-operational-verification.md). These observations are not real-shop valuation, independent physical-action or second-phone evidence.

At5be7f18, the corrected native two-page A4 PDF contains all three hashes exactly once and all byte counts, with capability absent and readable pagination. The recovered-runtime full gate passed24 infrastructure/339 API/19 frontend tests, no skips, plus lint/type/build. Both independent print reviews returned0 findings. Three actual factory dashboard reads returned200 with six shops and kept dataset count4→4. Local Must acceptance is complete; see UI and operational verification for the prior failures/recovery evidence. Hosted resources, production IAM, live fresh official flood coverage, native translation review and real-world accuracy are separate explicit limitations, not grounds to invent successful acceptance.

## Ownership after the gate

Astra personally owns the latest UI/research/correction work under the user's amended instruction. Root owns Git/GitHub, runtime restarts, real Telegram/browser operations and consent, emulator SDK/model windows and deployment authority. Tasks18/19 checkpoint1646ebc is committed and published in draft PR29, with no merge or hosting. Tasks20–22 source is frozen at the coherent reviewed v2 manifest plus independently reviewed query-lifecycle and volume/lifecycle supplements. Both axes returned0 after every correction. Exact SQL-copy and locked sequential/parallel application checks passed; the final25infra/629API/33frontend gate and primary runtime/browser restoration passed; root owns publication. No additional feature work, cloud deployment or CI follows from this checkpoint.

Each implementation slice gets focused checks, observed RED/GREEN for new guards, Astra source/correction review and separate independent Matt Standards/Spec reviews against a pinned committed baseline. Record implemented, locally accepted, provisioned and deployed separately. A common local gate may cover multiple stable slices but never conceals their individual acceptance gaps. Upcoming execution uses the latest parent-pinned documentation checkpoint with unchanged reviewed application as its baseline.
