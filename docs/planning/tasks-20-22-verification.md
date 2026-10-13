# Tasks 20–22: verification record

Tasks20 (waste sorting),21 (public check) and22 (outcome feedback/calibration) are **locally accepted** after independent review, the final corrected gate and actual primary-runtime/browser verification. The fixed review baseline is `1646ebca0fadae7afd5c50b4b189ecdac12426be`. Root owns the final commit/publication; no future SHA, deployment, merge or final submission is invented.

## Final accepted checkpoint

| Check | Final observed result |
|---|---|
| Infrastructure, rerun after retained-volume guard correction |25 passed,10.318s|
| API |629 passed, zero skips,80.09s|
| Frontend tests |33 passed, zero skips|
| Lint, typecheck, production build |Passed; full-gate-v3 exit0|
| Independent Matt Standards / Spec, including all supplements |0 / 0 outstanding findings|
| Restored primary API8000 |Eight reads, all available in1.01–5.57s; six seeded responses preserved|
| Actual Chrome dashboard3001 |Six synthetic shops; RM472 reported lifted, one vehicle, one real API acceptance, five virtual alerts; six seeded responses and0.99 calibration version2; unavailable official sources visible|

API count is **467 baseline +42 waste +36 public check +69 outcome +7 migration +8 query-lifecycle =629**. Infrastructure is24+one orphaned-volume regression=25. Frontend is22+six waste+five outcome=33. The complete run had already passed24 infrastructure cases before the last infra-only fix; the corrected25-case infrastructure suite was rerun separately, while unchanged API/frontend stages finished successfully. No post-freeze application changes were omitted. Logs are `full-gate-v3.log` and `infra-final.log` under `/Users/lucaslt/.codex/outputs/highground/task20-22-acceptance/`.

Primary runtime proof and browser results distinguish one existing real API acceptance from virtual alerts and synthetic response history. They do not establish real physical actions or valuation accuracy. The passing result includes the query-lock and retained-volume corrections below; it does not erase the earlier failures.

## Earlier complete gate and independent reviews

The earlier complete `./infra/test.sh` exited **0** against the frozen candidate plus its first emulator configuration supplement, before the subsequent live-runtime correction:

| Check | Observed result |
|---|---|
| Infrastructure |24 passed,9.495s|
| API |621 passed, zero skipped, six dependency warnings,200.79s|
| Frontend |33 passed, zero skipped|
| Frontend lint, type check, production build |All passed|

API accounting is **467 accepted baseline +42 waste +36 public check +69 outcome +7 migration =621**. Frontend accounting is22 baseline +6 waste +5 outcome =33; infrastructure remains24. Warnings are recorded as dependency warnings, not hidden or treated as test failures.

The complete log is `/Users/lucaslt/.codex/outputs/highground/task20-22-acceptance/full-gate-v2.log`. Independent Matt Standards and Spec reviews each returned **0 outstanding findings** after corrections. Both also independently reviewed the subsequent single-line emulator tuning and again returned0. Review snapshots include intended untracked files: `matt-review-v2/source`, its manifest and `supplemental-infra-review.json` under the same private output directory. Root verifies the acceptance commit matches these reviewed source bytes.

The earlier full attempt is retained:24 infrastructure passed;616 of619 API cases passed, with one stale assertion and two BigQuery create-dataset timeouts. The stale assertion conflated an invalid loss-condition enum with valid waste prompt wording; it now tests rejection through the actual wire schema. No passing claim was made for that attempt.

## Task 20 — waste and recovery

- Typed waste facts bind the frozen inventory and assessed clip. Valid loss estimates remain available when waste classification fails validation. Missing/unassessed/omitted unaffected items do not acquire invented waste quantities.
- Food/drink/medicine contamination rules are deterministic; destroyed, contaminated or uncertain items cannot become donation-eligible. An eligible assessed item still requires separate current-owner opt-in. No “safe salvage” promise is made.
- The latest completed assessment per shop/episode/inventory controls current facts; a newer unavailable assessment revokes older actionable consent and known totals while retaining history. Owner-confirmed streets are normalized, otherwise Unassigned. Public aggregates expose coverage and estimated load-equivalents, not required trucks or private identities.
- Actual Pro first produced contradictory contaminated salvage and failed closed. A corrected prompt produced a valid three-item block. A later actual six-item response omitted two unaffected waste rows; an exact captured-wire RED/GREEN regression added only canonical null-disposition/null-quantity normalization.
- A fresh integrated captured-output replay passed in12.911s through real local Firestore/GCS/BigQuery and application services: six unchanged baseline/loss/waste rows, worker denial, upload replay, protected report denial, three original hashes/ledger rows and public synthetic aggregate. This replay did **not** call Vertex again. The original unavailable report remains unchanged.
- Actual handler/Firestore street confirmation passed with virtual Telegram, including duplicate stability and old-action denial. Native four-page PDF checks passed: three full hashes exactly once, byte counts, simulation/estimate/limits/waste/food-rule text, capability absent from text and links, all pages visually inspected.

Evidence includes `waste-journey-result.json`, `waste-actions-proof.json` and `pdf-proof.json` under the private acceptance directory. Real-model estimates varied between runs; this is integration evidence, not a valuation-accuracy study.

## Task 21 — public location check

- Sender-bound requests expire after five minutes and enforce one lookup per30seconds. No signup or shop creation is required. Exact input coordinates stay transient; output uses rounded distances, source/time/hazard, separately labelled district warnings and public destination listings.
- Missing/stale/unavailable information never becomes an all-clear. Registered-owner active Danger and result Danger retain fixed-template precedence and final checks; optional constrained generation cannot override them.
- Actual official HTTP/local Firestore reader checks returned degraded JPS/MET status and two historical public destinations without private identities. This does not establish fresh coverage during a real flood.
- Configured Flash returned the constrained partial-summary key; recursive inspection of six persisted ADK documents found no private coordinates/shop/report/media/sender fields.
- Actual local handler/store verification passed with virtual Telegram: rate/expiry, duplicate update without resend, no signup, no persisted input point, and explicit captured-source replay provenance. Non-English error/overflow paths retain translation-review and uncertainty notices.

Evidence: `actual-public-sources-proof.json`, `actual-check-flash-proof.json`, `check-handler-proof.json`. A helper initially mistook lawful public-destination coordinates for leaked input because it used the same point; the corrected distinct input passed without an application change.

## Task 22 — response coverage and bounded calibration

- First current-owner response per confirmed shop/episode is immutable. Missing responses remain unknown. Prompts are due six hours after an accepted Warning/Danger or immediately after explicit closure, and active Danger defers them.
- Prompts visibly identify the confirmed UTC interval, or start plus “No closure recorded”; these are episode references, not owner-observed water times or assertions of current flooding. Actual response time is retained separately. Explicit owner-declared observation time is required for missed-inside ordering.
- Nonofficial Warning radius alone may adjust10% within0.5–1.5x using fresh disjoint batches within30days. Shrinking requires at least five responses. Growth requires confirmed inside flooding and complete history proving no earlier accepted or uncertain delivery. Official coverage, Danger and report corroboration radius remain unchanged.
- Exact immutable outbox facts, current demo generation and privacy allowlists control analytics. Public UI calls the measure response coverage/water reports, not accuracy. Synthetic fixture responses and real Telegram acceptance are counted separately.
- Actual store concurrency, uncertain-send handling, virtual callback rejection, fixture calibration0.9→0.99 and old-generation denial passed. Actual Firestore/BigQuery analytics passed duplicate, unavailable, generation and privacy cases.
- Final reviewed-source application-route/Firestore/BigQuery journey passed in32.07s on primary9050: repeatable six-episode seed, job authentication/limits, owner/worker/first-response, duplicate webhook, injected analytics failure and resumption without another prompt, synthetic-only projection and reset. Telegram was an in-process fake, with zero external sends.

Evidence: `outcome-store-proof.json`, `outcome-analytics-proof.json` and `outcome-journey-proof.json`; final rerun logs and frozen source manifests are retained alongside them. The protected local job is manually invoked; no hosted automatic schedule is claimed.

## Corrections, infrastructure and UI

Astra corrected review findings with a typed shared reply guard, typed outcome-store reads/exact acknowledgments and explicit episode-reference wording. Two prompt cases were observed RED then GREEN; focused pure rechecks passed107 cases, with21 emulator cases explicitly skipped in one pure batch. The final complete gate above subsequently ran all621 API cases without skips. Seven bounded configured-Flash calls added only two reference keys; prior catalog and Danger values remained unchanged.

The emulator's metadata-only nullable schema patch failed an actual new-column query. Root instead created a separate local `highground_v3`, copied all five table row multisets/hashes, verified new-column queryability and retained the original dataset. Only ignored local `BQ_DATASET` changed. No cloud migration or destructive fallback occurred.

Persistent BigQuery stalls were retained as failed evidence. Root's controlled same-data A/B passed25 focused integration tests with Go soft memory512MiB/GOGC100; the old256MiB/GOGC50 configuration had stalled. The runner changed only that environment pair, retaining pinned image, hard768MiB/swap1GiB, loopback port and persistent volume. The original stopped container and immutable backups were preserved. The reviewed-source journey and full gate then passed. This was a verified local recovery/configuration result, not a guarantee of permanent emulator reliability; Docker VM memory was not changed. Subsequent simultaneous live dashboard/outcome polling reproduced query/cleanup timeouts, so root paused polling and reopened runtime acceptance. Subsequent sequential requests also failed or exceeded the frontend deadline, so no concurrency fix is justified. Root is testing a fresh isolated database containing an exact copy of the configured five business tables while preserving the entire original database/history. No successful migration or root cause is claimed at this checkpoint.

### Latest runtime migration diagnostic — not yet accepted

After the green gate, live dashboard/outcome reads timed out, including sequential requests after a restart. Root preserved the original database/container/volume and prepared a fresh isolated emulator on9056 for an A/B test; primary API8000 and web3001 were stopped to remove polling interference. Another browser surface may have been polling earlier, but this remains a diagnostic possibility, not an established cause.

The first official `list_rows` copy is **invalidated**: REST `tabledata.list` reported two alerts with no continuation token although the immutable physical SQLite backup contains28; outcomes reported zero versus six physically stored. Matching source/target hashes from that incomplete API enumeration therefore did not prove complete preservation. `active-bq-copy-proof.json` is explicitly marked `passed:false`, the partial probe dataset is not accepted, and no runtime/configuration switch occurred.

Root's replacement diagnostic uses bounded30-second `query_rows` `SELECT *` into a distinct isolated `highground_v3_sql` dataset, validating schema and canonical row hashes against physical baseline counts: events8,alerts28,confirmations3,evidence_ledger13,outcomes6. Source before/after and target equality must all pass before adoption. The original `highground_v3`, its complete history and immutable backup remain untouched; this work has not justified an application patch or increased production timeout. The SQL copy subsequently passed exact schema and row-multiset comparisons at8/28/3/13/6, with source before/after unchanged. Fresh-clone sequential endpoints returned available in0.699/0.450s; parallel round1 passed, but round2 caused Docker OOMKilled=true/exit137 at the unchanged768MiB hard cap. Thus slow retained-catalog reads and unsafe concurrent query memory are separate observed failures. Root subsequently adopted the verified clone and passed the locked runtime checks recorded below.

The user-requested dashboard polish and Astra's drill handoff passed actual desktop/tablet/390px/320px checks: map hierarchy, long names without page overflow, keyboard table scrolling/focus, marker and event-popup focus through polling/removal, outside focus preservation and44px map controls. Selected-shop→drill→location handoff,46px action buttons and both report keyboard regions passed. Empty/unavailable states preserve uncertainty. The actual basemap loaded15 tiles; no failed-tile defect was asserted from an early screenshot. Report print styles remained unchanged.

## Remaining limits and submission work

- Hosting, deployed IAM/Scheduler, production storage semantics and cloud acceptance remain deferred by the user. Local model calls are actual Vertex requests; storage/application services are local.
- Native-language human review, independent shop-owner validation, real-shop valuation accuracy and a second physical tester are not established by these synthetic/local probes.
- The saved card is readable as a local file; no phone airplane-mode test is claimed. A final recorded video, deck, public deployment and timed human rehearsal are not completed by the2:45 shot list.
- Controlled tile-network-error/retry injection remains unperformed; actual successful tile loading and responsive interaction were observed.
- Source freshness, historical destination opening and model uncertainty remain visible. No route safety, scene authenticity, insurance payout, RM loss-prevention or calibration accuracy claim is made.
- No CI, Actions workflow, Dependabot, repository-connected deployment or Stretch implementation was added.

The approved creative demonstration is prepared in [single-shop-drill-runbook.md](single-shop-drill-runbook.md). Its coherent local card/dashboard/report artifacts explicitly identify recorded isolated stages rather than one uninterrupted live transaction; no private capability is committed.

### Query lifecycle correction and verification

The actual shared query helper now acquires one bounded in-process lock only after validating that the explicit emulator endpoint matches the actual loopback SDK client. It holds the slot through query submission, row materialization and exact owned result cleanup; acquisition failure raises before SDK work, and every exit releases the slot. Cloud queries never acquire it, and request/proxy timeouts remain unchanged. This protects one application process, not independent tools or multiple worker processes; emulator-heavy probes must still be coordinated.

Four new behavioral cases were observed RED against the prior helper: distinct SDK clients overlapped at query/result/cleanup, and the busy caller did not time out before starting SDK work. After correction,19 helper cases passed; the combined helper/outcome analytics run passed30 with one actual-SDK test explicitly deselected. Eight new cases cover those three phases, bounded wait, release after each failure phase and cloud bypass. The next complete API total is629=621+8; the earlier621-test full gate remains valid historical evidence but is not a post-correction gate. Both independent reviewers rechecked this frozen two-file delta and returned0 findings. Root then replayed the real endpoints successfully, as recorded below. No new library, cloud behavior change or timeout increase was introduced.

### Verified runtime recovery and final lifecycle supplement

The locked fresh clone passed actual application endpoint replay: two sequential requests and three concurrent pairs all returned available in0.46–1.19s. Evidence: `runtime-locked-probe.log` and `runtime-8004-proof.json`. This combines the exact SQL-preserved business dataset with serialized emulator query/result cleanup; it does not claim the old catalog alone was repaired or that unrelated processes can query concurrently.

The runner now names `highground-bigquery-live-data`; the approved active dataset is `highground_v3_sql`. Root owns the primary9050/container/config switch, preserving all original volumes, stopped containers and historical query jobs. Hard768MiB/swap1GiB, pinned image, loopback exposure, soft512MiB/GOGC100, SDK request timeouts and frontend deadlines remain unchanged.

Both supplemental reviewers caught a real lifecycle edge before acceptance: changing the current volume constant removed the recovered volume from fresh-initialization protection. Astra added its explicit historical name to the guard. A fake-Docker test where only that orphaned recovered volume exists was observed RED (empty initialization would proceed), then GREEN; all nine lifecycle cases and four subtests passed. No Docker mutation was performed by that test. The final infrastructure total is25=24+1. Root's full gate had already passed the prior24 infrastructure cases; the corrected25-case infrastructure suite then passed separately, and unchanged629 API/33 frontend/lint/type/build stages finished with exit0.

Final actual-browser evidence: `ui/final-dashboard.png`, `ui/final-dashboard-dom.txt` and `ui/final-dashboard-proof.json` record main3001 across14:14–14:15MYT polling, with available stats and six current seeded responses. Primary BigQuery was running and OOMKilled=false. These are observations of the corrected local runtime, not an uptime guarantee.

Final primary API8000 runs the frozen reviewed workspace through `uvicorn api.main:app`, so local renderer fonts, infrastructure schema files and demo assets remain available. The earlier partial non-test snapshot was a probe boundary, not the final application runtime. No application source change accompanied this launch.
