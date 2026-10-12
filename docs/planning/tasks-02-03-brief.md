# Tasks 2 and 3 — parallel implementation briefs

Authorized under the all-task instruction. Baseline: 142178f. Preserved source: docs/spec/01-build-spec.md. No hosted automation; actual cloud resource provisioning is deferred by the latest local-first instruction, even after the project is confirmed. The active gcloud project is unrelated and must not be used implicitly.

## Task 2 — infrastructure lane

Files: infra/setup.sh, small BigQuery schema files and focused local shell-command contract tests under infra; .env.example only for necessary explicit setup configuration. No API/frontend edits or dependency lock changes. Record official command/permission references and validation in docs/planning/infra-research.md.

Interface: an explicitly configured GCP_PROJECT and GCP_REGION (asia-southeast1 default); fail closed on missing project, missing tools, incompatible existing region/type or permissions. Provide read-only preflight/dry-run behaviour if useful; make actual setup deliberate, rerunnable and project-scoped. Do not create credentials, activate an unrelated project, print secret values or add secret versions from command-line arguments.

Steps: consult official gcloud/bq docs; enable required APIs; create or validate Firestore Native, private uniform-access media bucket, flood-events topic, highground dataset and five tables, runtime identity/least-privilege bindings, empty Telegram secret containers. Account for locally invoked source deployment prerequisites without repository triggers. Use explicit project flags; validate existing resource configuration before skipping. BigQuery evidence ledger must be insert-only in application usage and avoid gratuitous broad roles; document any permission distinction that ingestion will need.

Tests: shell syntax plus meaningful intercepted command-contract tests for missing project, existing compatible resources, conflicting resources and failures. Never claim these tests prove provisioning. Root will perform actual setup only after hosting/resource provisioning is authorized.

Done locally: script/schema files are valid, repeat-run/fail-closed behaviours verified and secrets/regions/scopes correct. Done externally: actual required resources and least-privilege paths verified in confirmed project. Keep separate statuses.

Pitfalls: Firestore immutable location, globally unique bucket collision, bq regional dataset, secret rotation versus empty container, unintentional inherited active project, echoing tokens, ledger writer permissions, no hidden CI/triggers.

## Task 3 — data lane

Files: api/models.py for a minimal shared Warning/source-result contract; api/tools/datagov.py; captured raw response fixtures; focused parser/client/dedupe tests. No api/main.py/requirements/env changes; ask Astra before new dependencies. Use existing httpx and validated typed records. Research skill applies: investigate primary source APIs/docs in background execution and save citations/observations/recommendations to docs/planning/data-source-research.md.

Interface: injectable HTTP transport and observation clock; common validated source/identity/level/observed-time/geography/reason record; source freshness/status separate from zero warnings. Parsing must not invent coordinates/districts. Stable event identity/status/lifecycle dedupe should allow genuinely new observations/escalation without permanently suppressing later flood episodes. Keep dedupe boundary explicit for later persistent integration.

Steps: fetch both actual endpoints; save original captured responses plus capture provenance; inspect authoritative fields/type semantics/timezone documentation. Map flood severity from water_level_indicator, never ON/OFF device status; reject null/error/malformed/nonfinite coordinates and stale timestamps for alerts. Disregard malformed/non-monotonic threshold sets as a basis for invented severity. Weather heavy-rain wording in marine warnings is insufficient: require verified warning type, valid window and geographic applicability; unsupported shape remains visible as unsupported rather than silently no risk.

Freshness configuration: expose an explicit parameter with user-approved 90-minute default for station readings, using Asia/Kuala_Lumpur interpretation only if source semantics verified; future integration may configure it. This is an engineering exclusion threshold, not a guarantee of official update cadence. Root has recorded user approval; do not manufacture a current feed. Current known feed latest non-null date is February 2024.

Tests: captured shapes plus small synthetic cases for stale/null/error/future dates, timezone boundaries, marine false positives, unknown geography, duplicate/escalated/new-episode identity, pagination/error/network/invalid-JSON handling as applicable. HTTP errors must report unavailable without crashing future polling. Pure tests do not require cloud access.

Done: both endpoints are inspected/captured; parser/client contract documented; meaningful tests pass; source health reports current observed stale condition honestly. Live official warning acceptance remains unresolved if upstream data is stale.
