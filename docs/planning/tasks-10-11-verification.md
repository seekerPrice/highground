# Polling, active risk and inventory — in-progress verification

Review baseline: `1a4d7b1345b61dda187b1302138333bcdf18e48f`. Tasks 10/11 remain in progress; no independent Matt acceptance or hosted Scheduler acceptance is claimed. Root owns the shared API runtime and all live restarts. Task 8/9 publication is separate and does not include these working changes.

## Astra corrections and review

Task 10 review identified older observations being accepted for dispatch despite a newer source observation, incomplete final official freshness enforcement, and simulated official-source entries being eligible for real official recovery. Sol added typed rejection reasons, final 90-minute checks and a demo recovery exclusion. A further crash/recovery ordering seam required checking the durable official source watermark both before applying an event and immediately before delivery: a pending old Danger cannot send after fresh NORMAL, even when no shop risk record existed yet or the alert was already prepared. A further same-source severity watermark check suppresses a queued Warning once the source has escalated to Danger, even before any shop risk record exists. Both intent orders are covered. Sol passed 63 affected tests after these corrections. Astra independently inspected the final application/delivery checks and passed **42 risk, polling, Scheduler authorization and dispatch tests in 6.37 seconds**, with no skips.

Task 11 review identified that an empty/unassessable extraction could replace an existing baseline and mark inventory known. The correction retains the attempted assessment privately, returns an unavailable result, preserves a valid prior baseline and does not turn uncertainty into zero stock. Original media remains immutable. Actual source review confirms strict domain validation remains after a simpler provider-compatible structural response schema.

Astra independently ran inventory, stock confirmation and Scheduler authorization checks: **17 passed, one actual-GCS test skipped because that endpoint variable was absent, in 3.48 seconds**. The skipped public onboarding/native-video/original-storage/refresh test was then run with both actual Firestore and GCS emulator endpoints: **one passed in 0.75 seconds**. These are affected checks, not the final complete local gate.

## Configured model evidence

Sol's actual configured Pro baseline extraction passed in **10.361 seconds**, returning six visible groups at confidence 0.85 from the 899,251-byte labelled synthetic still-derived clip. Five persisted ADK events totalled 13,530 serialized bytes and contained no inline media. Counts and estimated values differ from the generation brief; this is transport/schema/useful-extraction evidence, not valuation or real-shop accuracy. Earlier provider schema failures and an empty extraction produced no accepted inventory. Root's separate exact-20-MB transport probe is documented in video-input-research.md.

## Remaining gates

Finish the integrated accepted Warning → exact immutable Stock Done confirmation and actual BigQuery metric regressions; freeze a candidate for root's full local gate and local synthetic journey checks; then run separate Matt Standards and Spec reviews on explicit committed SHAs and correct/recheck any findings. Actual Telegram video upload, second-phone testing, native translation review and hosted IAM/Scheduler acceptance remain separate limits.


## Frozen local candidate

Both execution lanes are frozen for root's consolidated gate and candidate commit. Task 11's combined affected suite passed **134 tests in 15.42 seconds**; its final focused checks passed **31 tests with one analytics test skipped**, and that isolated official-client BigQuery stock/episode aggregation check then passed separately in **3.10 seconds**. No new dependencies or analytics schemas were added. Astra independently inspected accepted-message/snapshot binding and reran the actual ADK request-payload plus stock confirmation tests: **four passed in 0.99 seconds**, the separately verified BigQuery check deliberately deselected, two upstream warnings. The Warning→accepted Stock Done path freezes the exact displayed value even after baseline refresh, and owner/worker duplicates share one action fact.

The next steps are the complete local gate, root's frozen integrated journey, and independent Matt Standards/Spec review. No task completion is claimed before those checks.


## Observed failures versus added coverage

No red-before-green claim is made for the inspection-discovered active-risk ordering, recovery isolation/freshness or empty-inventory corrections: their tests were first observed after correction. Task 10 did observe a concurrent Firestore transaction lock timeout during implementation and authentication test-seam failures; these are distinct from proof of an authorization bypass. Task 11 observed an existing dispatch test fail after a catalog-key collision, then pass after restoring the existing key. A ranking fixture quantity error and an outdated mocked factory seam were test corrections. A Burmese callback was measured at 243 characters and shortened to 168, including the translation notice, before the passing length test was added.

Actual provider diagnostics separately observed SDK rejection of exclusive numeric bounds/integer enums, two HTTP 400 responses for incompatible schema variants, then successful structural-schema responses. The first successful response was empty with an inappropriate comparison explanation; the corrected baseline instruction produced a validated estimated inventory. No failed or empty assessment was accepted as a new known baseline.

Root's complete frozen local gate passed **6 infrastructure and 212 API tests**, four upstream warnings, plus frontend lint, typecheck and production build. The API suite grew from 175 to 212 tests. This is the pre-review candidate gate; root subsequently identified an old Stock Done callback potentially remaining valid after demo reset clears the canonical episode. That finding is pending reproduction/correction and the candidate is not yet accepted.

## Independent Matt review of d9038e9

Pinned nonempty comparison: `1a4d7b1345b61dda187b1302138333bcdf18e48f...d9038e91ac38530a60f39aad0d63234327d761fd`.

Standards reported **one P2**: stock confirmations remain eligible after recovery/reset closes the canonical episode because the mismatch guard ignores a null current episode. No additional actionable heuristic findings.

Spec reported **one P1 and one P2**. The P2 independently matches the stock finding. The P1 concerns source episode attribution: an old active Danger followed by queued NORMAL and a new-episode Danger can retain the old episode ID while advancing its timestamp, preventing either episode's later recovery from clearing it. This was reproduced with pinned transaction doubles. No additional scope-creep findings.

Both findings were returned to the corresponding Sol owners for actual Firestore failing regressions before correction, followed by focused checks and independent review rechecks. Candidate d9038e9 is not accepted.

Root's frozen synthetic native-video journey passed its application assertions in **12.211 seconds** using actual Pro, Firestore, GCS, evidence ledger and BigQuery with synthetic download/virtual Telegram edges: five estimated groups at confidence 0.85, four lift-first items, exactly RM628 displayed/confirmed/aggregated, one fact after duplicate callbacks, and no revaluation after refresh. The overall probe exited 1 because isolated BigQuery dataset cleanup timed out; this is not described as a successful whole command. Cleanup disposition is tracked separately by root. No real Telegram video latency or valuation accuracy is claimed.

Root subsequently resolved cleanup with a persistent emulator restart and deletion of only the isolated probe dataset/topic; cleanup retry exited 0. All five application tables remained readable, with four existing application events and four alerts retained. The initial full-probe exit remains recorded as 1; successful assertions and successful later cleanup are separate evidence.

## Correction evidence before the follow-up commit

The closed-episode defect was observed failing in three actual Firestore cases before the fix: demo reset, photo Danger followed by owner recovery, and official Danger followed by matched recovery. Requiring an open matching canonical episode in stock preparation and confirmation made those cases pass, with no new fact/outbox from old buttons and successful new-episode buttons. Astra's independent stock rerun passed **six tests in 2.81 seconds**, with the unchanged analytics check deliberately deselected.

The source-episode defect was observed failing in two of four actual Firestore ordering cases before correction (new Danger first, with/without another unresolved source). Separate episode-keyed recovery receipts retain accepted observation attribution without an embedded growing map. Additional review observed two failing aged-receipt cases before tightening application-time freshness: a historical receipt cannot clear official Danger due to an unrelated fresh event. Same-source historical attribution may carry the Danger latch into the current source episode until a fresh explicit recovery.

Astra also found early transient model failures were not retried. Actual SDK 429/503 and transport-timeout cases were observed failing before correction. They now receive at most one further attempt within the unchanged total budget; permanent 400 and exhausted total deadlines do not retry. Astra independently passed **27 inventory/stock tests in 3.81 seconds**, including actual GCS, with only the unchanged analytics test deliberately deselected.

Root identified that the approved configurable freshness cutoff was not wired end to end. A real parser→poll factory test with a five-minute setting incorrectly emitted a six-minute Danger and was observed failing before propagation. The correction uses one bounded `OFFICIAL_MAX_AGE_MINUTES` setting (1–90, default 90), including final risk/recovery checks. Final correction freeze, backend gate and both independent review rechecks remain pending.

The correction slice is now frozen. Sol's final risk/OIDC/dispatch checks passed **56 tests in 11.75 seconds**, no skips. Astra inspected the final receipt/attribution/freshness implementation and both mutating factories, then independently reran the affected actual-Firestore source ordering, aged receipt, nondefault cutoff and tightening cases: **12 passed in 5.97 seconds**, 13 unrelated cases deliberately deselected. Photo/inventory stores currently only read canonical risk; future recovery entrypoints must receive the same configured policy. Root's affected backend gate and independent Matt delta reviews follow the correction commit.
