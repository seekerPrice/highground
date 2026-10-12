# Local emulator preservation checkpoint — 13 October 2026

Root performed a coordinated runtime migration after both implementation workers paused emulator tests. This is local development evidence, not production durability or cloud acceptance.

## Actions and boundaries

- Stopped only the previously reviewed HighGround API on loopback port 8000 so it could not write during migration or later encounter unsupported virtual fixtures. Its tunnel was not reconfigured; application availability remains paused until the reviewed replacement starts.
- Inspected exact current Pub/Sub and GCS container identities, pinned images, commands, port exposure, labels/mounts and ownership through the lifecycle runner. Firestore and BigQuery were not stopped or replaced.
- Backed up five HighGround-only GCS buckets, all three original objects and two Pub/Sub topics through official SDKs against the exact local endpoints. Pub/Sub had zero subscriptions, so no queued subscription messages required transfer. Backup bytes and a private manifest remain outside the repository.
- Stopped and renamed the two old containers to `highground-pubsub-unbounded-retained-2215` and `highground-gcs-unbounded-retained-2215`. They were not deleted. Replacements were created with `infra/emulators.py`'s exact service specifications.
- Restored the same bucket/object identities, object content types/metadata and topic identities. Read every restored object back and checked SHA-256 and byte length against the backup. The process did not rewrite application evidence records or claim original emulator object-generation numbers were preserved.

## Observed results

All commands exited 0. Post-migration status:

```text
highground-firestore: running; bounded configuration=True
highground-pubsub: running; bounded configuration=True
highground-gcs: running; bounded configuration=True
highground-bigquery: running; bounded configuration=True
```

Independent post-restore readback:

```json
{"mode":"verified","buckets":5,"objects":3,"topics":2,"sha256_all_match":true}
```

Observed container memory use immediately afterward was approximately 304 MiB for Firestore, 209 MiB for Pub/Sub, 39 MiB for GCS and 309 MiB for BigQuery. Limits are 768 MiB for Firestore/Pub/Sub/BigQuery and 256 MiB for GCS; instantaneous usage is not a sustained-load guarantee.

## Limits

This was an explicit backup/restore operation, not proof that an ordinary emulator restart preserves data. Firestore, GCS and Pub/Sub remain ephemeral under the documented runner; acknowledge disposable data before stopping them or arrange preservation separately. Old retained containers are recovery context, not a reason to start duplicate services. BigQuery continues on the previously verified recovered persistent volume. No unrelated service, Docker VM setting, cloud resource, webhook, hosted deployment or CI configuration changed. A final application/integration gate and reviewed application restart remain separate acceptance steps.
