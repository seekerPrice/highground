# Destinations, confirmations and media — review record

Code baseline: `8818a934ce91ed22c49f0891f5dabb65892697ef`. Task 8 is locally accepted; Task 9 implementation is reviewed, with actual live photo upload acceptance pending consent. Hosted and second-phone acceptance remain deferred. Historical review steps below distinguish candidate failures from the final result.

## Early concrete review findings

- Preserve separate source/coordinate attribution, unknown current opening and unknown parking floor. Fictional registry points cannot become real-world route instructions. A future sourced floor must retain its own provenance in the immutable action snapshot.
- Internal simulation, original processing time and composition-budget fields must not become caller-controlled public simulation inputs. Same-request fingerprints must remain stable on retries.
- Media facts need confirmed-shop versus confirmed-shared location provenance. Telegram downloads remain on their fixed origin with redirects disabled and bounded byte reads, including existing GCS objects on retry/verification.
- Photo assessment preserves the source's street/entrance/inside/none distinctions, nullable nonnegative depth and bounded reason. Negative/staged/unrelated assessments do not become corroborating evidence. Two-report corroboration requires distinct shops and media/report deduplication.
- Photo processing transitions must check lease ownership, as media transitions already do, to prevent a canceled/expired worker overwriting a later retry.
- Inline image bytes passed as ADK `new_message` would be persisted in Firestore session events. [Firestore's documented document limit is 1 MiB](https://docs.cloud.google.com/firestore/quotas), below the labelled demo PNG size even before base64 encoding. Persist media ID/hash text and inject actual bytes only into the model request through a supported callback; verify that actual model input contains the image while persisted events contain no inline media. Apply the same constraint to later video tasks.

Corrections and their actual regression/integration results will be recorded before a candidate is frozen. Root owns the shared runtime restart, live Telegram checks and candidate commits.

## Task 8 candidate checks

Sol's combined destination/confirmation/dispatch/webhook/onboarding checks passed 83 tests with one explicitly skipped multi-sink test because its additional emulator variables were absent. Its latest affected checks passed 37 tests. Astra independently inspected the actual destination, immutable action, callback and media-routing files and reran the vehicle/webhook checks with Firestore: **30 passed in 7.25 seconds**, no skips. These focused results do not replace the upcoming complete local gate or live acceptance.

Root seeded exactly two sourced historical destinations into the local registry and verified lookup returns Pasar Moden Sri Muda parking and Dewan Kenanga PPS. Opening remains unknown; no floor number is invented.

## Remaining integration checks

Live own-chat confirmations/photo flow, the full local gate and both independent Matt axes remain pending. The BigQuery emulator reports successful additive schema updates without making new columns queryable. Root preserved the existing dataset and copied exact row multisets to local `highground_v2` with final schemas: two events and two alerts retained, all new columns queryable, source unchanged. Switching ignored configuration awaits the planned runtime restart. This is an emulator compatibility workaround, not production migration evidence.

The source's two-report fallback includes confirmed, non-rejected unverified reports. Model unavailability cannot silently remove this independent corroboration rule. Two distinct shops with different original-byte identities may produce Warning within 500 metres/30 minutes; explicit negative/staged/unrelated/screenshot/old assessments, unconfirmed locations and duplicates are excluded. Corroboration alone never produces Danger or implies model verification.

## Task 9 focused evidence

Sol's media/photo/official-client emulator suite passed **23 tests in 3.87 seconds**. The actual configured Flash/ADK probe assessed the exact 2,837,741-byte synthetic-after image in **6.158 seconds**, persisted a validated schema and five session events totaling 9,576 serialized bytes, with no non-null inline media in those events. The model-input test separately verifies the exact original bytes reach the model request. This establishes multimodal transport and durable trace behavior, not real-shop accuracy or total neighbour delivery latency. Final transient-error and Danger-race regressions are still in progress.

The later combined run passed 50 tests but failed one official sink test before dataset creation because the local BigQuery endpoint refused the connection. Reporter Danger invalidation and concurrent Danger regressions passed. This infrastructure failure is not counted as a green full gate; root is inspecting the shared emulator before live verification.

Root confirmed a second emulator OOM (exit 137 at 19:23:18 UTC). Both in-memory analytics datasets were lost; the earlier copy/verification result remains historical evidence only. Firestore and GCS stayed available. Root is preparing bounded-memory, persistent local BigQuery storage and will restore synthetic analytics from authoritative Firestore facts, recording that reconstruction boundary explicitly. No unrelated containers are changed.

The final frozen Task 9 focused run passed **50 tests in 4.25 seconds**, with the unavailable BigQuery integration explicitly deselected. Final Danger regressions include blocking a lower-level neighbour event when Danger arrives during assessment, invalidating the reporter's vehicle action on photo Danger, and replacing a raced location/photo prompt immediately before sending. The full all-emulator gate remains pending.

For Telegram photo acceptance, compare stored SHA-256 with the exact bytes Telegram returns. Telegram may resize/recompress a local PNG sent as a photo; preserving downloaded upload bytes does not prove identity to the file before Telegram processed it.

Astra independently reran final photo and persisted-payload checks against Firestore: **22 passed, one BigQuery test explicitly deselected, two upstream ADK/Firestore warnings, 2.12 seconds**. Actual source review and correction rechecks are complete; independent Matt axes follow root's committed candidate.

## Independent review of candidate ac0cfdd

Pinned comparison: `8818a934ce91ed22c49f0891f5dabb65892697ef...ac0cfddfd76f48016d13716e4bf77d32236cece8`, validated nonempty before separate reviewers ran.

Standards identified one P1: contradictory `unreadable` plus assessed/high-confidence inside-water output passed validation and could trigger Danger. Spec independently identified the same defect and a second P1: setting the reporter's active Danger before a failed dispatch caused retries to return early without ever creating the neighbour event. No additional heuristic or scope-creep findings were reported.

Both defects are corrected in the frozen follow-up: unreadable output must remain uncertain without positive water/depth assertions; persisted immutable Danger triage resumes its exact stable dispatch after failure without reassessment, while lower-level reports still obey active Danger. Sol passed 27 focused tests; Astra independently inspected the changes and passed the same **27 tests in 1.18 seconds**. Both reviewers' focused rechecks remain outstanding. Original candidate ac0cfdd is not accepted.

Root replaced only the failed local analytics container with persistent named-volume storage and bounded Go memory settings. Both datasets and the two original event/two alert rows were reconstructed exactly from Firestore; all five tables and rows survived a deliberate container restart and the new columns are queryable. This is reconstructed analytics, not survival of the failed in-memory datasets. Ignored local configuration now selects `highground_v2`.

## Follow-up review and full local gate

Both axes confirmed the original findings resolved in `e74902e8e7c708d8a3a4ee7514050111b0a126dd`, but independently identified a new P1 in the retry correction: it also bypassed the 30-minute freshness cutoff for prepared Danger. The final frozen correction restores the unconditional cutoff. A retry after 31 minutes preserves the existing Danger state and saved intent but creates no event, sends no new neighbour alert and performs no model reassessment. Immediate eligible retries still recover. Sol passed 28 focused tests; Astra inspected the change and independently passed **28 tests in 1.31 seconds**. Final reviewer rechecks remain pending.

Root's complete `infra/test.sh` at e74902e passed **6 infrastructure tests and 171 API tests**, no skips, three upstream warnings, plus frontend lint, typecheck and production build. Persistent BigQuery survived that workload. This gate preceded the final freshness-only correction; the affected 28-test rerun verifies that delta without repeating unchanged frontend checks. Live own-chat vehicle/photo checks remain separate acceptance evidence.

Both independent axes rechecked final freshness commit `ceda0935881fdb8a18ccca1fbcfdcfb8a2280adb` and reported **zero outstanding findings**. Root's subsequent real destination-enabled Warning exposed a separate persistence defect: Telegram's nested keyboard arrays cannot be stored directly in Firestore. The event remained pending with no alert prepared or message sent. Sol is correcting the storage boundary and adding actual Firestore Warning/vehicle/routes and Danger-route round-trip regressions. Local acceptance is still pending that correction and its live/review verification.

The frozen storage correction serializes markup as JSON at rest and restores the exact Telegram object on retrieval, preserving absent/None and legacy object records. The actual Firestore regression reproduces the former error, resumes the same pending Warning with vehicle plus two route controls, verifies no resend on replay, and dispatches route-only Danger. Sol's broader affected checks passed **61 tests with one explicitly skipped additional-sink test**; Astra independently inspected the boundary and passed **12 real Firestore Task 8 tests in 5.36 seconds**. Commit, independent delta rechecks and actual live retry remain pending.

The correction was committed as `52544e32cb3b3cad1e1f2830d7a10e33dddb03f5`; both Matt axes reported zero outstanding findings on the explicit delta. Root independently passed 40 vehicle/photo tests, then restarted the local API and recovered the exact pending live Warning: HTTP 200, one accepted alert. Clicking the actual own-chat Vehicle moved control twice produced one confirmation fact and one BigQuery row. Its immutable snapshot exactly matches the accepted alert; both self-reported and simulation flags are true. No duplicate alert was sent.

Live UI inspection revealed Telegram's automatic Google Maps preview was misleading despite correct Malaysian coordinate links. The final narrow wire correction disables automatic link previews while retaining explicit route text/buttons. Sol and Astra independently passed 21 webhook/wire tests (Astra 3.10 seconds). Its final commit/review is pending; the existing runtime has not been hot-reloaded. Actual live photo upload remains pending explicit upload consent and is not counted as completed.

## Final reviewed implementation and current acceptance

Final code baseline for the next milestone: `1a4d7b1345b61dda187b1302138333bcdf18e48f`. Both Matt axes independently rechecked the preview delta and reported **zero outstanding findings**. Root verified the corrected preview through actual Bot API and Chrome: no automatic preview, explicit Malaysian routes/buttons retained, vehicle action target earlier than stock.

Root then ran the complete local gate at this exact candidate: **6 infrastructure tests, 175 API tests, no skips, three upstream warnings**, plus frontend lint, typecheck and production build, all passed. BigQuery used the restored persistent local dataset. All relevant findings were corrected and rechecked before reporting. Task 8 local acceptance is complete. Task 9 live photo upload remains pending explicit upload consent; neither its live neighbour-delivery latency nor actual second-phone acceptance is claimed. Tasks 10/11 may proceed independently under the approved all-task authorization.
