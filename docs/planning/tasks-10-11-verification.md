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
