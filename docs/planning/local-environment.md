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

## Earlier persistent BigQuery runtime after the second OOM

At19:23:18UTC the in-memory BigQuery process was killed again (`OOMKilled=true`, exit137). Both the original and copied datasets were lost. Root retained the stopped container as `highground-bigquery-oom-20261013` and started the same pinned0.8.1image as `highground-bigquery`, with named volume `highground-bigquery-data`, `--database=/data/bigquery.db`, `GOMEMLIMIT=256MiB`, `GOGC=50`, a768MiB container memory limit and1GiB memory-plus-swap limit. Only the loopback9050 port is published. No unrelated project was stopped or reconfigured. The image's own `--help` confirmed the persistent database option.

Both datasets were recreated with their corresponding schemas. The two prior synthetic events and two accepted alert rows were reconstructed from the unchanged Firestore event/alert facts with their original identities and timestamps, then compared field-for-field against those facts. This is reconstruction after loss, not proof that the earlier in-memory copy survived. All other three tables were empty before the loss. A deliberate restart of the new container preserved all ten tables and expected rows; new nullable columns also queried correctly afterward. `.env` now selects `BQ_DATASET=highground_v2` for the upcoming application restart.

The bounded persistent configuration subsequently completed the full local gate (6 infrastructure tests, 171 API tests with no skips, frontend lint/typecheck/production build, exit 0). The process remained available afterward; this does not establish that host memory pressure is eliminated. The existing SDK returns a500 for creating an already-present dataset in this emulator, so the recovery procedure inspected dataset existence before creation instead of assuming `exists_ok=True` handles that emulator response.

## Tasks 10/11 local runtime checkpoint

The API was restarted on reviewed candidate `8d28cc8f72d51f61a519035bd8bc4b9b47267e7e`, bound to `127.0.0.1:8000`, with access logging disabled. The ignored mode-0600 `.env` enables `LOCAL_DEVELOPMENT=true` and `SCHEDULER_LOCAL_AUTH=true`; both remain false in the committed example. Local operator authentication additionally requires demo mode and the loopback Firestore emulator. Production Google OIDC is a separate acceptance surface.

Actual HTTP probes returned health 200, unauthenticated polling 403 and authorized local polling 200. JPS and MET both reported degraded status and zero intents were processed; this does not claim all-clear or validated live warning coverage. The successful repeated probe completed in0.508 seconds. Its first harness assertion incorrectly expected401 rather than the route's documented403; correcting that expectation required no application change. The global fixture collection contained one explicitly synthetic shop and no non-demo shops before the probe.

The final synthetic video journey at `033a8da` completed all assertions and cleanup with exit0 in9.410 seconds, using actual configured Pro and local Firestore/GCS/BigQuery with virtual Telegram delivery and synthetic download. Its displayed, confirmed and aggregated estimated stock value matched. Subsequent `8d28cc8` changes affect recovery/confirmation state, not the model/media integration; all243 backend tests passed after those changes. No application cloud resources were deployed.


## Current BigQuery runtime after query-result accumulation recovery

During Tasks12/13/15 verification, the pinned emulator was OOM-killed at both768MiB and1536MiB limits. Increasing the cap did not fix the workload. Root backed up the complete SQLite volume and verified integrity, then used a separate reversible copy for diagnosis. Official query-job metadata identified106 derived result datasets whose dataset/table identifiers exactly matched the query job UUID. Only these proven derived results were removed from the copy; all19 retained physical business/job/history tables had identical SHA256 content, and SQLite integrity passed. The original database and backup were preserved.

An isolated test container on loopback9051 using that copy at768MiB then passed all three previously failing BigQuery integration tests in5.09s, with observed resident memory188.6MiB. Root adopted the recovered volume **`highground-bigquery-recovered-data`** for the current `highground-bigquery` service on loopback9050, retaining the same pinned image and768MiB limit. The original volume **`highground-bigquery-data`** remains intact, and the stopped original container is **`highground-bigquery-oom-2117`**. The temporary9051 container was stopped. No Docker VM or unrelated project settings changed.

This A/B result establishes recovery for the tested query workload; a final consolidated gate is running. Task17 must prevent anonymous result datasets from accumulating during long-lived dashboard polling, using a tested, supported explicit scratch-result lifecycle with concurrency isolation. Do not repeat direct database recovery as ordinary application cleanup. Root retains the copied-database recovery script, table comparisons and result evidence outside the public repository.

## Firestore replacement after the image-build-window OOM

Root observed that the original ephemeral Firestore emulator was OOM-killed during the serial image-build window (reported finish time2026-10-12T21:36:43Z). No intentional stop occurred. The earlier270-test API gate predates this loss and remains historical evidence; it does not establish that development fixtures survived. The private recovery browser fixture and previous own-chat Firestore records must be treated as lost unless rebuilt and reverified.

The stopped container is retained as `highground-firestore-oom-2136`. Its replacement `highground-firestore` uses the same pinned Google emulator image, loopback8787,768MiB memory/1GiB memory-plus-swap, and `JAVA_TOOL_OPTIONS=-Xms64m -Xmx384m`. Root's actual official SDK create/read/delete smoke passed for highground-2026-lucas; resident memory was268.5MiB. Focused tests may resume with fresh isolated namespaces. Pub/Sub remained available at293.8MiB but still requires bounded Java configuration in Task17. No unrelated service changed. Task16 will rebuild approved synthetic scenario records; private report/browser acceptance must use a newly created fixture rather than claim recovery of the lost one.

## Tasks20–22 post-gate analytics diagnostic

The reviewed source passed the complete24infra/621API/33frontend gate, but restored live dashboard/outcome polling exposed query/cleanup timeouts afterward; sequential calls also reproduced them. Final runtime acceptance remains open. Primary API8000 and web3001 are stopped during root's isolated A/B work, with the original retained BigQuery volume untouched. The latest runner settings are soft512MiB/GOGC100 with the existing hard768MiB/swap1GiB limits, not a Docker VM increase.

A fresh9056 `list_rows` copy was rejected before any switch: `tabledata.list` omitted physical rows (alerts2vs28,outcomes0vs6) without a continuation token. The proof is invalidated, and the partial target is a probe only. Root is instead testing a separate `highground_v3_sql` copy through bounded SQL enumeration and physical baseline counts8events/28alerts/3confirmations/13evidence/6outcomes, checking exact schemas and row hashes before/after. Original databases, job history, containers and immutable backups remain preserved. No successful migration, root cause or product fix is claimed until the SQL copy and actual request checks pass. The complete evolving evidence is recorded in [Tasks20–22 verification](tasks-20-22-verification.md).

The replacement SQL copy subsequently passed exact physical baseline counts8/28/3/13/6, complete row-multiset/schema comparison and source-before/after equality. Fresh sequential endpoints were fast, but overlapping queries caused an observed OOM at the unchanged hard768MiB cap. The corrected shared query helper now uses an endpoint-validated, bounded in-process emulator-only slot spanning submission/materialization/cleanup; cloud calls bypass it. Actual locked-clone application replay then passed two sequential requests plus three concurrent pairs, all available0.46–1.19s.

The runner's adopted volume is now `highground-bigquery-live-data`, with active dataset `highground_v3_sql`; root coordinates the actual switch and retains original volumes/containers/history. Fresh initialization explicitly refuses all three known live/original/recovered volume names, even if their historical container is missing. Soft512MiB/GOGC100 and hard768MiB/swap1GiB remain; no Docker VM increase or SDK/proxy timeout expansion occurred. Final post-correction gate is still being recorded; do not mistake the earlier621-case gate for the new629-case result.

Final recovery acceptance passed: corrected infrastructure25tests, API629tests without skips, frontend33tests without skips,lint/typecheck/production build all passed. Both independent reviewers returned0 after the query and retained-volume corrections. Primary9050 now uses the proved `highground-bigquery-live-data` volume/`highground_v3_sql` dataset; original volume/container/history remain retained. Actual primary8000 returned eight available reads1.01–5.57s, and Chrome3001 remained available across14:14–14:15MYT polls with six seeded responses,0.99 calibration and honestly unavailable official feeds. BigQuery was running with OOMKilled=false at final observation. This supersedes the diagnostic pending states above without claiming cloud behavior or perpetual emulator reliability.
