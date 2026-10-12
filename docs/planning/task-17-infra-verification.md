# Task 17 infrastructure slice — implementation checkpoint

Scope: local lifecycle runner, explicit test scope, and local-operation documentation. Application query-result cleanup, replay/resumer hardening and Task 16 fixtures remain separate work. Hosting is deferred.

## Files and interface

- `infra/emulators.py`: fixed four digest-pinned service specifications, `start`, `status`, `stop`, optional exact `--service`, and explicit `--ack-disposable-data` for ephemeral stops. Docker calls have a 30-second outer timeout; stop asks Docker for 20 seconds. No removal, volume deletion, migration or broad-prefix selection exists.
- `infra/local_gate.py` and `infra/test.sh`: full mode by default, exact loopback endpoint configuration/reachability, actual JUnit skip rejection. `--unit` labels intentionally limited coverage and sets empty endpoint values to prevent dotenv from reintroducing integration endpoints. No shell source/eval is used; existing python-dotenv reads endpoint values only for the runner.
- `infra/tests/test_local_lifecycle.py`: seven command-contract tests with the Docker mutation boundary replaced by a fake.
- `README.md`: current architecture, setup/run/check commands, privacy and synthetic/service limitations. No host bootstrap or hosted automation added.

Before adoption or stopping, the runner checks exact name, inspected immutable ID, image identity, command/entrypoint, ownership labels where present, loopback-only ports, privileges and exact volume boundary. Previously unlabeled containers require the same exact configuration checks; legacy absence of labels is not a broad ownership match. Start additionally requires the planned resource limits/heaps, refuses mismatches, and rechecks exact ID/configuration before mutation. Current persistent BigQuery volume is required to exist; lost retained data is never silently replaced. Original OOM containers and original volume remain outside the selected names and are untouched.

## Evidence

Observed read-only `python3 infra/emulators.py status`: all four current services running; Firestore and BigQuery bounded configuration true, Pub/Sub and GCS false. No service was stopped, recreated or changed. Root supplied a private current runtime inventory; machine-specific paths and container IDs are not committed here.

`python3 infra/tests/test_local_lifecycle.py -v`: seven passed. `bash -n infra/test.sh`: passed. The cases cover ephemeral-stop refusal, changed-ID refusal and ID-targeted stop, foreign image/port/mount/ownership refusal, unbounded legacy start refusal, pinned loopback/resource creation and retained-volume requirement, exact endpoint/full-versus-unit scope, and rejection of a real JUnit skipped testcase.

Observed RED: a temporary copy removed the two ephemeral acknowledgment checks; `LifecycleTests.test_ephemeral_stop_requires_explicit_disposable_ack_before_commands` failed with `ValueError not raised`. GREEN: unchanged implementation passed the full seven-case file. Only fake Docker mutation calls were used; the temporary copy was removed. Other cases were added from source inspection and were not separately observed failing against earlier code.

## Pending acceptance and limits

This execution lane performed no shared runtime mutation. Root separately completed the bounded Pub/Sub/GCS replacement with verified fixture restoration, as recorded below and in `local-environment.md`. No Firestore/GCS export or restart durability is claimed. Current BigQuery recovered-volume provenance and prior restart observations are in `local-environment.md`; this runner has not repeated preservation tests. Full current integration/frontend gate has not been rerun during concurrent Task 16 work. TCP reachability is preflight, not application/service acceptance; the full tests and zero-skip result remain required.

The strict gate uses exactly the recorded loopback endpoints and rejects cloud-looking values. Unit mode intentionally skips integration; it does not certify deployed permissions, model quality or a complete Must journey. Hosted M1/M3/M4/M5/M6 and Google OIDC/IAM remain deferred.

## Fresh-install correction

`start --service bigquery --initialize-new-data` explicitly permits a fresh labeled volume only when no current/historical HighGround BigQuery container and neither known retained volume exists. Other actions/services reject this flag. Default start still requires the retained volume and never substitutes new empty data for a missing database. The new test was observed RED first (`unexpected keyword argument initialize`) before implementation, then GREEN; all eight lifecycle/gate cases passed. Only fake Docker calls ran. No existing container/volume was changed.

Astra independently read the implementation and reran all infrastructure tests after the explicit fresh-initialization correction: 18 passed in 4.284s. This is command-contract coverage with fake mutation boundaries, not actual service start/stop or full application acceptance.

## Root runtime migration update

Root separately replaced Pub/Sub/GCS with bounded configurations and restored exactly five buckets, three original objects with matching SHA-256 and byte lengths, and two topics. All four services now report bounded configuration true. Old containers remain retained; Firestore and BigQuery were not restarted. This actual root migration is distinct from this lane's fake-command tests and establishes the checked restoration only, not automatic Firestore/GCS restart durability. See `local-environment.md` for root's runtime record. Earlier unbounded status above is historical pre-migration evidence.

## Query and setup-failure hygiene checkpoint

The current-job query helper was observed RED when materialized rows were returned without cleanup, then passed eleven fake-boundary cases. One root-coordinated actual SDK SELECT passed in 4.25 seconds: rows remained usable after exact job-destination dataset deletion, and the official client returned NotFound for that dataset. Production never cleans result datasets; local cleanup requires actual validated loopback client configuration and exact project/job/dataset/table binding. Cleanup failure/refusal is explicit, and query/result failures retain their original exception.

Three isolated official-client integrations (dispatch Pub/Sub/BigQuery, immutable media Storage/Firestore/BigQuery, stock aggregation) then passed with zero skips in 22.78 seconds. SELECTs assert the helper's cleanup status is cleaned. Resource creation is inside an exact-ID cleanup scope, registered before create calls; NotFound is tolerated, all cleanup/client-close callbacks are attempted independently, and cleanup errors preserve the primary exception through a bounded class-name note or fail the test when no primary exists. A fake setup-failure regression was observed RED with cleanup disabled (topic deletion was never called), then both pure cleanup cases passed unchanged. Whole owned test-dataset deletion was subsequently raised to the approved bounded 25-second timeout; query-result helper bounds remain unchanged. No broad job/resource listing or application dataset cleanup was introduced.

Exact-namespace ADK cleanup for selector/photo tests was queued at this checkpoint and is now completed as recorded below.

## Exact ADK namespace cleanup completed

Selector/photo test paths now create the cleanup client and register namespace cleanup before model/session execution or assertions. Independent async cleanup callbacks close selector/assessor and owned clients, retain the primary error with bounded cleanup-error notes, and fail otherwise successful tests on cleanup failure. The recursive helper uses `list_documents` (including missing parent references) and traverses only each test's exact random root/subcollections; each SDK call is bounded and has retry disabled. No collection-prefix scan or unrelated record deletion occurs.

Three pure cleanup cases passed in 0.70 seconds. After coordinating the Firestore slot with the backend lane, the two affected actual ADK session tests plus a synthetic missing-parent/nested-event assertion-failure regression passed with zero skips in 0.69 seconds. Models were injected local fakes; no remote Gemini, BigQuery or GCS work ran. The regression retains the original AssertionError identity and verifies the nested event is absent after finally cleanup. SDK warnings concern ADK's experimental schema feature and shipped positional Firestore filtering; neither indicates a failed check. The earlier three multi-service probes remain separate evidence.

Frontend Task 16 DTO binding was checked with eleven focused contract/operator tests after the simulated-count correction, plus type checks and focused lint. Browser/production rebuild acceptance remains root-owned; no frontend build ran while the root preview was serving.

## Explicit local application resource initializer

`infra/local_setup.py` defaults to read-only resource inspection; `--apply` is the explicit creation opt-in. Before constructing any clients, it requires local-development/demo mode, all four validated loopback endpoints, explicit configured project/topic/dataset, the local `highground-media-<project>` bucket naming convention, and valid reviewed schemas. It inspects existing topic/bucket/dataset identities and all five table field-name/type/mode signatures before any create operation. Only absent configured resources are created, with bounded calls and retry disabled. Permission errors never mean absence. Existing incompatibility fails without dropping/recreating/migrating data. Local bucket naming is not cloud IAM ownership evidence. All owned client-close callbacks are attempted independently; original failures remain primary and cleanup errors are exposed through sanitized exception-class notes.

Observed RED used a temporary in-process validation bypass: the missing-endpoint regression failed because the analytics factory was called. The unchanged implementation then passed six fake-SDK cases: endpoint refusal before clients, compatible resources with zero creates, dry-run missing resources with zero creates, exact absent-resource creation/verification, permission-error refusal with independent closure, and schema mismatch before any dependent creation. Python compilation passed. Astra independently read the implementation and reran all six cases in 0.008 seconds with no findings.

No actual SDK inspection or resource apply ran in this execution lane. Root's actual local dry-run/apply acceptance remains pending after candidate review; no provisioning/cloud call, runtime change or durability guarantee is inferred from fake tests. README records the two commands and required local settings.
