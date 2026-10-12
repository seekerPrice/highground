# Local-first environment — 13 October 2026

The user approved creating a dedicated HighGround project and selecting their named billing account, while deferring application hosting. Project `highground-2026-lucas` was created and billing linkage succeeded. Vertex AI API is enabled solely to call the required Gemini models from local development. Infrastructure resources and Cloud Run deployments have not been provisioned by infra/setup.sh.

## Telegram

With explicit user approval, BotFather created [@highground_flood_copilot_bot](https://t.me/highground_flood_copilot_bot). Bot API getMe returned ok:true with that username. Its generated token and random webhook/hash/operator secrets are stored only in the ignored .env, mode0600. A temporary local tunnel webhook was subsequently registered and verified with no pending errors; actual own-chat onboarding, restart recovery and Warning/Danger delivery passed. See task-05-live-verification.md and tasks-05-07-verification.md. The tunnel URL is temporary, not a hosted deployment. No other project bot was changed.

## Firestore emulator

A Docker container named highground-firestore runs the official Google CLI image `gcr.io/google.com/cloudsdktool/google-cloud-cli:588.0.0-emulators`, digest `sha256:be2f0e582a94c9e06e7a384fe2b3b39d590eeb8da65a110eda991598c100fe80`. Host binding is loopback only, `127.0.0.1:8787`. Logs confirmed the emulator started. Use FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 for local Firestore clients. Emulator availability is not proof of application persistence behavior; integration tests remain necessary.

Container command:

```bash
docker run -d --name highground-firestore -p 127.0.0.1:8787:8787 gcr.io/google.com/cloudsdktool/google-cloud-cli:588.0.0-emulators gcloud emulators firestore start --host-port=0.0.0.0:8787 --project=highground-local --quiet
```

Do not rerun this creation command while the named container exists. Use docker start highground-firestore after stopping it. The emulator data is temporary and restarting the emulator clears it; restarting only the app must preserve conversation records in the still-running emulator. Do not present emulator storage as deployed persistence.

Official references: [Firestore emulator](https://docs.cloud.google.com/firestore/native/docs/emulator), [Google CLI Docker image](https://github.com/GoogleCloudPlatform/cloud-sdk-docker).

## Gemini candidates

The configured fast model is documented [Gemini 3.8 Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash), the configured Pro candidate is [Gemini 3.1 Pro preview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-pro), using the global endpoint. Names live in .env, not application source. The first REST probes returned200 for both, but Pro exhausted the deliberately tiny128token output budget before producing valid JSON. A modelHTTP200 is not structured-output acceptance. A subsequent google-genai2.29.0 async SDK probe used explicit HighGround quota project, Pydantic response_schema and1024outputtokens. Both configured models produced schema-validated status=ok; exit0. This also verifies the existing local ADC works when the quota project is explicitly overridden for this client, without modifying global credentials. Subsequent actual ADK Warning composition persisted a validated selection/session and delivered to the own-chat fixture; fixed Danger bypassed the model. A tiny synthetic blue-video Pro probe established inline video/schema connectivity only. Inventory, damage accuracy and the full photo-to-neighbour latency target still require their own task evidence.

## Pub/Sub emulator

Docker highground-pubsub runs the same official CLI emulator image, bound only to127.0.0.1:8797. PUBSUB_EMULATOR_HOST is configured locally. The emulator accepted creation of projects/highground-2026-lucas/topics/flood-events withHTTP200. No cloudPub/Sub topic exists yet. A subsequent official Python SDK probe created a unique subscription, published one synthetic JSON event, pulled the exact message, acknowledged it and removed the probe subscription; exit0. Task7's application event/outbox integration subsequently passed with the emulator in the full local gate; see tasks-05-07-verification.md. This is not production Pub/Sub acceptance.

## Organizer portal inspection

Read the authenticated [challenge page](https://hack2skill.com/event/aibuildercup2026/dashboard/challenges) in Chrome. Sustainability & Social Impact explicitly includes disasterpreparedness/communityresilience and suggests Gemini onVertexAI, BigQuery, CloudStorage, CloudRun andPub/Sub. This supports the selected track/stack; it adds no new mandatory appfeature. The portal's resources and ongoing/upcoming submission panels were empty during inspection; judging percentages and exact submission fields are not independently confirmed from those panels. No form was submitted or team changed.

## Local media and analytics emulators

The production stack remains Cloud Storage and BigQuery. Local test tools use the same official Python clients with explicit endpoint overrides and anonymous credentials:

- `highground-gcs`: [fake-gcs-server](https://github.com/fsouza/fake-gcs-server), image `fsouza/fake-gcs-server:1.56.1`, digest `sha256:797ce226d62f947c009dc40246b30cfb456b8473d8241407f9d6f2c04e4d69ef`, bound to `127.0.0.1:4443`. HTTP mode with external URL `http://127.0.0.1:4443`. Local bucket `highground-media-highground-2026-lucas` exists.
- `highground-bigquery`: [bigquery-emulator](https://github.com/goccy/bigquery-emulator), image `ghcr.io/goccy/bigquery-emulator:0.8.1`, digest `sha256:f4e428d265a93dc5ce36c294e1c584c7c9b384117d47ab8ddbb63d8d50b7f393`, REST bound to `127.0.0.1:9050`. Project `highground-2026-lucas`, dataset `highground` exist locally. No host gRPC port is exposed.

Observed SDK smoke: Cloud Storage uploaded synthetic binary bytes with generation precondition, downloaded identical SHA-256 bytes, then removed the probe object. BigQuery created a unique probe table, inserted a synthetic row using `insert_rows_json`, queried the exact result, then deleted that table. Exit 0. These checks do not substitute for application integration tests.

`STORAGE_EMULATOR_HOST` and `BIGQUERY_EMULATOR_HOST` are configured only in the ignored local `.env`. The latter must be explicitly wired into BigQuery `ClientOptions(api_endpoint=...)`; it is an application convention, not assumed SDK auto-detection. Emulator authentication must never be selected for cloud endpoints.

Both tools are third-party development emulators. The GCS emulator does not validate signed URL signatures or expiration, and BigQuery does not implement IAM. Local results cannot prove cloud permission boundaries, signed-link expiry, production service behavior or deployment acceptance. Keep both endpoints private to loopback; expose only authenticated application routes through any Telegram test tunnel. Firestore/GCS storage is temporary; BigQuery was subsequently moved to a dedicated persistent local volume as described below. All records remain synthetic development data.

During Task7 verification, the BigQuery container stopped at18:26:54 UTC with Docker reporting `OOMKilled=true`, exit137. The shared Docker VM has about5.8GiB and also runs unrelated projects. Root reproduced connection refusal, restarted only `highground-bigquery`, observed successful dataset-list HTTP, and recreated/verified all five reviewed base schemas through the official SDK. Resident memory after reseeding was about175MiB. This restores the test service; it does not establish that memory pressure is resolved. Earlier emulator rows were disposable and lost, so resumed integration tests use fresh identities. Serialize emulator-heavy checks for now; Task17's reproducible local runner should bound HighGround emulator resource use without stopping other projects.

Before Task8/9 live schema changes, two isolated nullable-column probes exposed another emulator limitation. Both official SDK `update_table(..., ['schema'])` and GoogleSQL `ALTER TABLE ... ADD COLUMN` returned success, but a subsequent query could not resolve the new column. This is observed behavior of the pinned local emulator, not a production BigQuery limitation. Both disposable probe tables were removed; the existing application tables and Task7 records were untouched. Do not treat a successful schema mutation response alone as migration acceptance.

Root subsequently created local dataset `highground_v2` with all five finalized schemas and copied the old synthetic rows through the official SDK. Exact row comparison passed for every table, the old dataset was verified unchanged, and SQL successfully selected every column in each new table. Preserved counts: events2, alerts2, confirmations0, evidence_ledger0, outcomes0. New nullable fields: confirmations.action_id/episode_id/self_reported and evidence_ledger.location_source. The old dataset remains intact. The live app will switch through ignored `BQ_DATASET` only at the planned stable runtime restart; this is a local emulator compatibility procedure, not a production migration or cloud namespace change.

The first failed query also showed that `retry=None` does not disable the BigQuery SDK's separate query-job retry policy. Set `job_retry=None` on diagnostic query/result calls as well as request retry/timeouts; otherwise a retryable emulator internal error can outlast the intended result wait. Root interrupted only its own probe and the cleanup completed. This is a diagnostic correction, not evidence of a completed application hardening change.

## Current BigQuery runtime after the second OOM

At19:23:18UTC the in-memory BigQuery process was killed again (`OOMKilled=true`, exit137). Both the original and copied datasets were lost. Root retained the stopped container as `highground-bigquery-oom-20261013` and started the same pinned0.8.1image as `highground-bigquery`, with named volume `highground-bigquery-data`, `--database=/data/bigquery.db`, `GOMEMLIMIT=256MiB`, `GOGC=50`, a768MiB container memory limit and1GiB memory-plus-swap limit. Only the loopback9050 port is published. No unrelated project was stopped or reconfigured. The image's own `--help` confirmed the persistent database option.

Both datasets were recreated with their corresponding schemas. The two prior synthetic events and two accepted alert rows were reconstructed from the unchanged Firestore event/alert facts with their original identities and timestamps, then compared field-for-field against those facts. This is reconstruction after loss, not proof that the earlier in-memory copy survived. All other three tables were empty before the loss. A deliberate restart of the new container preserved all ten tables and expected rows; new nullable columns also queried correctly afterward. `.env` now selects `BQ_DATASET=highground_v2` for the upcoming application restart.

The bounded persistent configuration subsequently completed the full local gate (6 infrastructure tests, 171 API tests with no skips, frontend lint/typecheck/production build, exit 0). The process remained available afterward; this does not establish that host memory pressure is eliminated. The existing SDK returns a500 for creating an already-present dataset in this emulator, so the recovery procedure inspected dataset existence before creation instead of assuming `exists_ok=True` handles that emulator response.
