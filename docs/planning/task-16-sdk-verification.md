# Task16 isolated emulator acceptance — 13 October 2026

Root froze the Astra-reviewed Task16 source into an out-of-repository snapshot with a SHA-256 manifest, then ran a one-off application probe against actual Firestore, GCS, Pub/Sub and BigQuery emulators. Every probe resource used a unique namespace/bucket/dataset/topic; global records and the retained report fixture were untouched. The probe exited 0, with its core journey completing in 24.584 seconds.

## Observed journey

- Seeded six explicitly synthetic shops, three vehicles and two sourced historical destinations. The baseline inventories were labelled synthetic fixture estimates; no model inference was invented.
- Stored six actual original MP4 objects and read each back through the storage service. All SHA-256 hashes matched the source bytes and receipts. Six distinct evidence-ledger media identities were observed with an actual BigQuery query.
- Repeated seeding preserved every media record and object identity. Fixture receipts used `origin: local_fixture` with no fabricated Telegram timestamp.
- Exercised the real authenticated simulation and dashboard/reset routers with the real dispatch/risk/action stores and sinks. Warning produced six virtual alerts, followed by Danger producing six virtual alerts. No Telegram transport or model call occurred; the composer used its deterministic fallback. Earlier configured-model acceptance is separate evidence.
- Dashboard analytics returned available state with six simulated virtual alerts and zero real Telegram acceptances, vehicle confirmations or stock confirmations. Virtual messages contained no Telegram action buttons or invented message IDs.
- Missing and wrong reset credentials returned 403. Authorized reset completed generation 2. Replaying the previous Warning identity was superseded and the current dashboard excluded old events/counters.
- A fresh Warning produced six new virtual alerts. Repeating the already-completed reset request returned its original receipt without clearing that new activity.
- The ordinary non-demo Danger sentinel and all original evidence records remained identical. No confirmation records were fabricated.

## Cleanup and query lifecycle

The probe materialized query results before removing only each captured current query's eligible destination (`project` matched, and dataset/table IDs equalled that job's ID). It never listed jobs or deleted by broad prefix. Task16's frozen dashboard did not yet include Task17's lifecycle integration, so the probe explicitly cleaned its own captured result objects; this is not a claim about background application cleanup.

Finally, the probe removed only its own exact Firestore namespace (including subcollections beneath missing parents), GCS objects/bucket, BigQuery dataset and Pub/Sub topic. Cleanup completed successfully. Global application resources and the retained private report fixture were not modified.

## Separate current-resource setup check

After releasing the probe's resources, root ran `.venv/bin/python infra/local_setup.py` against the actual configured emulators. It exited 0 with:

```json
{"mode":"dry-run","missing_resources":0,"verified":true}
```

This inspected the topic, bucket, dataset and all five reviewed table schemas. No `--apply` operation was needed or run. Fresh-resource creation currently has fake SDK tests; this read-only observation does not claim actual fresh provisioning or cloud ownership/IAM verification.

## Pending acceptance

These checks were pending at the initial isolated probe. They subsequently passed at the reviewed f6efd315 checkpoint: see task-17-operational-verification.md for global six-shop seeding, consenting-owner binding, actual production reset/retry, protected manual recovery and the corrected full gate/reviews. Actual report PDF output still needs desktop unlock. Two-phone/media-upload/hosted acceptance remains separately deferred. No Should code, CI or deployment was introduced.

## Actual isolated initializer apply follow-up

Root subsequently exercised `initialize(..., apply=True)` with an exclusively owned temporary topic/dataset and five schema tables, while the existing approved shared bucket was only inspected. All configured endpoints remained loopback; no cloud operation occurred. The command exited 0:

```json
{"dry_run":{"mode":"dry-run","missing_resources":7,"verified":false},"apply":{"mode":"apply","missing_resources":7,"verified":true},"repeat_apply":{"mode":"apply","missing_resources":0,"verified":true}}
```

This substantiates actual missing-resource creation and repeatability for the topic/dataset/tables. The exact temporary dataset and topic were cleaned in `finally`; the shared bucket was not changed. Creation of a previously absent bucket by this initializer remains fake-SDK coverage (the separate Task16 probe created a real isolated bucket through the same official storage SDK).

## Integration finding returned to Sol

The actual stale-event replay response includes `reason: obsolete_scenario` with `status: superseded`. Root observed the frontend operator parser allowed only event ID/status/alerts, so it would reject this legitimate response before clearing the preserved request identity. The finding was returned through Astra for a focused regression and contract correction. The real backend probe passed; the later corrected frontend and actual lost-response/reset/retry operator journey passed (task-17-operational-verification.md). The production web process was stopped before those source edits and the final build.
