# Task 17 — remaining backend recovery and local query lifecycle

This is the next bounded backend slice after Task 16's shared dispatch/scenario interfaces freeze. Preserve the source spec, approved amendments and current local-first scope. No Should implementation, deployment or CI. Root controls runtime restarts, fixtures, external operations and commits.

## Files and ownership

Backend Sol may add a small recovery-job service/router and focused tests, then make necessary changes in `api/main.py`, existing outbox stores/services and local operation documentation. Integrate the separately owned `api/tools/bigquery_queries.py` helper into the dashboard and affected integration tests only after its contract is frozen. Frontend/infra Sol owns that helper and its focused tests until handoff. Avoid duplicate abstractions, new dependencies or a general job framework.

## Recovery contract

- Add an actual authenticated, bounded entrypoint for pending dispatch, confirmation analytics and stored-media evidence-ledger work. Reuse exact Scheduler authorization, including its explicit local operator guard, rather than an unauthenticated endpoint or a new credential. Provide the corresponding local manual command and deferred scheduling instructions; do not create cloud jobs.
- Inspect actual stores before wiring: stock confirmations inherit `VehicleConfirmationService` and share the confirmation collection, so one pending-confirmation scan can flush both kinds. Dispatch already has `resume_pending`; media has `resume_ledger` but no pending scan. Resume only ledger entries with originals already stored; do not invent Telegram file identities or redownload missing uploads without the original authenticated webhook replay.
- Use bounded batches and existing leases/idempotency identities. One unavailable item must not permanently starve unrelated stages. Reuse final Danger, episode and Task 16 generation checks for every dispatch replay. Respect already-started ambiguous Telegram requests; do not resend uncertain sends or claim physical exactly-once delivery.
- Return stage outcomes without private identifiers, raw SDK errors or secrets. Close owned clients. Bound SDK calls and total work honestly; cancellation of an awaiting thread does not establish that its underlying external request stopped.
- Demonstrate an outage that leaves durable pending facts, then invoke the real protected HTTP route after recovery and prove pending work completes with one logical confirmation/receipt, no duplicate message and no stale-generation send. Include missing/wrong authorization and non-local bypass refusal. Do not describe recovery as automatic until a running schedule actually exists; the manual authenticated endpoint itself is reproducible local recovery.

## Query lifecycle and test hygiene

Provide the missing reproducible local resource initialization step: create only absent configured Pub/Sub topic, private-emulator bucket, dataset and the five reviewed tables through official clients, after validating all endpoints as loopback. Inspect existing schema/ownership and refuse incompatible existing resources rather than recreating them. Fresh emulator startup alone does not establish these application resources. Keep initialization separately invoked and idempotent; tests/full gates must not silently provision or destroy shared development resources.

Integrate the reviewed query helper while preserving dashboard query parameters, billing bound, result validation and unavailable-state behavior. Only explicitly configured loopback emulator queries may delete their own materialized result destination, with exact project and `dataset_id == table_id == job_id` checks. Production queries never use this cleanup. Surface cleanup failures without dropping already materialized results or hiding the original query error. No job listing, broad-prefix cleanup, shared scratch table or direct database mutation.

Fix the observed dispatch integration setup leak: creation belongs inside the cleanup boundary, every exact resource cleanup is independently NotFound-tolerant, and a failed deletion must not prevent remaining cleanup/client closure. Use bounded query/result calls with `job_retry=None` and the same exact result cleanup in the dispatch, media and stock emulator tests. ADK namespace cleanup must traverse missing parent document references and subcollections rather than only existing parent snapshots.

Run observed RED/GREEN regressions for the real recovery entrypoint and setup-failure cleanup, focused actual-emulator checks in isolated namespaces, Astra source/correction review and both Matt axes at the parent-pinned candidate. Coordinate one final consolidated gate with root; do not run overlapping model probes, image builds or bulk service tests. PDF/remaining browser checks and actual lifecycle migration remain separately recorded Must gates.
