# Destinations, confirmations and media — review record

Code baseline: `8818a934ce91ed22c49f0891f5dabb65892697ef`. Both tasks are in progress. This note records review work, not acceptance.

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
