# Task16 local synthetic scenario

Implementation baseline: `6ccc9b06341d5ed0b285a02c21f6c03ce2959f52` (reviewed application `f914f9a`). This note records the Task16 backend slice; consolidated acceptance and both review axes remain root-owned.

## Seed and operator binding

The command requires an existing private emulator bucket and initialized evidence-ledger schema. It validates all four explicit loopback endpoints before constructing a client or mutating data: `FIRESTORE_EMULATOR_HOST`, `STORAGE_EMULATOR_HOST`, `PUBSUB_EMULATOR_HOST`, and `BIGQUERY_EMULATOR_HOST`. It refuses cloud/missing/malformed endpoints. Set `LOCAL_DEVELOPMENT=true`, `DEMO_MODE=true`, and `DEMO_VIRTUAL_DELIVERY=true`, then run locally:

```sh
.venv/bin/python -m api.demo_seed
```

The six stable IDs are `demo-t16-1` through `demo-t16-6`; three have vehicles. Every baseline points to a private original of the exact committed synthetic-before MP4, with its actual SHA-256, byte length and append-only ledger identity. The inventory is a manually defined synthetic estimate, explicitly labelled as such; it is not a model result or validation of real recognition/valuation accuracy. Local fixture receipts have `origin=local_fixture`, no Telegram receipt date, and unconfirmed synthetic coordinates. The two historical sourced destinations are created only if absent, with opening/floor status still unknown.

Repeat seeding preserves existing registrations, consent bindings, baseline pointers, original timestamps, inventories and completed ledger progress. IDs owned by unrelated registrations are rejected. Interrupted storage/ledger progress can be retried with the same command; physical ambiguous streaming duplicates are deduped by stable media identity. No report, action, confirmation or original is deleted.

Default delivery is entirely virtual: six server-owned string recipients, zero fabricated Telegram IDs. The actual factory enables this only with local/demo flags and validated loopback services. Durable alert status `simulated` and provenance `local_virtual` represent no external call, message ID, acceptance, reading or real self-report. The dashboard separates the BigQuery-backed virtual count from real Telegram API acceptance and latency. No virtual confirmation metric is invented.

Root may explicitly bind a known already-consenting registered owner, using its existing private registration ID:

```sh
.venv/bin/python -m api.demo_seed --bind-fixture 1 --registered-shop EXISTING_REGISTRATION --consenting-owner
```

Binding is **alerts and confirmations only**. Ordinary onboarding/session, baseline, photo and recovery-report routing continue to resolve the owner's ordinary shop. No ordinary shop or session is rewritten. Repeat seeding preserves the binding. Dangling binding flags are rejected. Actual two-account binding remains dependent on root's known consenting recipient facts; the default six virtual fixtures do not establish that source acceptance check.

## Reset boundary

Authenticated `POST /demo/reset` requires `{ "request_id": "stable-operation-id" }`; the client retains that identity through ambiguous or partial retries. The response has `status=reset|resetting`, `generation`, nullable `scenario_started_at`, `shops_reset`, `inflight_outcomes_unknown`, and a delivery note. Completed requests return their immutable prior result rather than clearing a newer scenario. A different request during partial reset is rejected/retryable.

Reset first writes a transactional `resetting` fence, then captures its bounded synthetic scope. Seeded scenarios capture only existing owned synthetic records from their six server-owned fixture IDs; absent partial-seed entries do not block reset. Dashboard projection and demo delivery targets use this fixture scope, so unrelated demo fixtures remain unchanged and invisible; legacy synthetic scenarios remain bounded to fifty and exclude ordinary shops. New demo creation, risk application, action preparation, callbacks and final send start check this same generation/state. Each shop closure and reset progress update checks the exact request/generation inside its transaction, preventing delayed duplicate reset from closing new-generation risk. Partial reset resumes after restart. Current dashboard event/alert/confirmation queries filter generation before bounded limits; BigQuery metrics additionally whitelist those current IDs, excluding late historical sink rows.

Already-started external sends cannot be unsent. Reset stays `resetting` until existing delivery leases drain. Expired unreleased leases have unknown outcomes, explicitly counted; a ready boundary does not claim their external requests were cancelled. Immutable original bytes, receipts, reports, action snapshots, confirmations and history remain.

## Recorded development evidence

- Actual Firestore initial RED: three failures (missing server generation, delayed old Danger accepted, send start permitted during reset), then GREEN after transaction fences.
- Actual seed/scope race RED: seed between old scope snapshot and fence left old Danger active after reset (`1 failed`, exit1, 0.47s). Capturing scope after the fence made it GREEN.
- Interrupted-seed/reset RED: after first fixture finished and second original failed, reset could not complete because five scoped shops did not exist (`1 failed`, exit1, 0.35s). Capturing only existing owned fixture records resolves that deadlock and preserves resumable seed progress.
- Duplicate-reset regression: isolated source copy disabled only the request/state/generation mutation guard; actual Firestore test then cleared fresh Warning (`1 failed`, exit1, 0.85s). Current guarded source passed. Temporary source copy removed; shared source/runtime never reverted.
- Focused scenarios exercise seed repeatability and real fixture bytes with explicit storage/ledger doubles, unrelated registration preservation, factory privilege rejection, receipt-origin validation, partial/restart/duplicate resets, creation/scope/model/send races, delivery-only virtual transport, old callback invalidation and fresh immutable confirmations. These tests do not claim actual GCS/BQ seed acceptance.
- Global seeding, actual GCS/BQ fixture ledger verification, real consenting phone delivery/binding, UI reset interaction and report print review are root-owned acceptance checks. No deployment, cloud provisioning, model call or external message was performed by this implementation lane.

Task17 owns manually invoked protected resumption, the bounded query-result lifecycle helper integration and fresh emulator resource initialization. This Task16 slice does not claim those existing helper methods run automatically.

Astra independently reviewed the corrected application paths and ran all scenario/dashboard cases after the final fixture-scope correction: 26 passed, zero skips, in 1.54s. Frontend contract/operator recheck passed 11 cases after fixing rejection of successful `simulated` alert counts. Independent Matt axes and the combined current candidate gate remain pending.

Root's subsequent [actual SDK journey](task-16-sdk-verification.md) passed against all four local services with six original hashes and six distinct ledger identities, repeated seeding, virtual Warning/Danger, reset, stale replay and duplicate-reset preservation. It exposed a frontend mismatch: the real superseded response includes a bounded `reason`, which the strict parser rejected. Sol observed the actual reply fail before the narrow whitelist correction; Astra reviewed the corrected parser and independently passed all 12 current contract/operator cases in 62.85ms. Known suppression reasons are validated but never reflected as arbitrary UI text, and the terminal superseded result permits a new simulation identity. Current combined gate and independent review remain pending.

Astra independently reviewed the Task16 source/corrections and ran scenario/dashboard tests: **26 passed, no skips, 1.54s**. The lane’s final affected gate was **116 passed, one analytics-env skip, 23.88s**; after the last scope validation, **26 passed, no skips, 2.34s**, compile exit0. Root captured the frozen Task16 export and SHA manifest before Task17 source edits.

## Review correction at8be5884

Both independent review axes identified that copying a registered owner into fixture recipients made shared media/report lookup ambiguous and could bypass the ordinary shop's final Danger prompt guard. The operator binding now carries `recipient_scope=alerts_confirmations_only`. Shared lookup and media authorization exclude only the narrowly validated owned fixture binding; the prior committed owned binding/provenance shape is recognized when scope is absent. Ordinary synthetic test registrations still resolve, and genuinely ambiguous ordinary registrations still fail closed. Dispatch and vehicle/stock callback authorization remain intact; ordinary records and immutable seeded receipts remain unchanged.

Actual Firestore RED: ordinary lookup returnedNone after binding and pre-existing Danger left a baseline prompt (`2 failed`, exit1, 0.87s). Corrected source passed both. Additional scoped-binding callback regression proves the bound fixture still sends one alert and records exact vehicle/stock displayed snapshots through public callbacks. Repeated seed preserves binding; a legacy binding without explicit scope preserves ordinary lookup too.

Final correction checks before the parent gate: Sol passed 37 scenario/recovery cases with no skips in 3.13s; Astra independently passed the nine targeted binding/history/outage cases in 1.54s (28 unrelated cases deselected), both exit0. The first full gate at8be5884 passed 24 infrastructure, 332 API and 19 frontend tests, all with no skips, plus lint/type/build. That candidate received Standards1/Spec2 findings described above and in task-17-recovery-verification.md; corrected full gate and independent rechecks are still pending.
