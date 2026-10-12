# Task 14 — local packaging, hosting deferred

Implementation baseline: `6ccc9b06341d5ed0b285a02c21f6c03ce2959f52`; reviewed application source `f914f9aed9379298af43cf476d81a8cd78a7280b`. The current local-first instruction supersedes Task 14's older immediate-deployment date. Hosted M1/M3/M4/M5/M6 acceptance is pending authorization and actual execution.

## Files and commands

Six packaging files were copied byte-for-byte from the external `task14-staging` artifact directory: `api/Dockerfile`, `api/Dockerfile.dockerignore`, `web/Dockerfile`, `web/.dockerignore`, `infra/deploy.sh`, and `infra/tests/test_packaging.py`. The deploy helper retains executable mode `0755`. No application, dependency-lock, runtime or CI configuration changed in this slice.

Build contexts, when explicitly scheduled:

```sh
docker build -f api/Dockerfile -t highground-api .
docker build -f web/Dockerfile -t highground-web web
bash -n infra/deploy.sh
python3 infra/tests/test_packaging.py -v
```

API uses the repository-root context with a Dockerfile-specific allowlist for Python source, committed translations and frozen requirements. Web uses its own context with an allowlist for application code, configuration, lock and local public assets. Both exclude private environment files, host dependencies, tests and private fixtures. Official Python 3.12 and Node 24.14.0 Debian images are pinned by registry manifest digest; requirements install with `--no-deps` followed by `pip check`, and web installs with `npm ci`. Both serve on `0.0.0.0` using runtime `PORT`, default `8080`, with non-root users and bounded local health checks. `HIGHGROUND_API_ORIGIN` is server-only runtime configuration, absent during the web build.

## Observed command-contract evidence

The four packaging tests passed after copying into the repository. Shell syntax passed. The existing local entrypoint discovers `infra/tests/test_packaging.py`; a consolidated gate remains the parent coordinator's separate check.

An observed RED run removed only the hosting authorization check in a temporary copy outside the repository. `PackagingTests.test_execution_requires_hosting_authorization` failed with `AssertionError: 0 == 0`: unauthorized execution incorrectly succeeded against fake `gcloud`. The same test passed against the original unchanged staged helper and asserted no fake command log was created. Original helper SHA-256 remained `5a15bd878fc9037d87e779b1eb46a780e7dd49bf173b2f878f5511420e6bdc47`. The temporary copy was removed. This proves the local guard's sensitivity, not cloud IAM enforcement.

Tests also cover default dry-run making no external calls, explicit deployment targets and versioned secret references, and fail-closed rejection of the unrelated project, plaintext secrets in runtime files, hosted local-auth bypass and noncanonical backend origins. All command executions in these tests use a temporary fake executable; none contact cloud services.

## Root's actual image evidence

Root supplied the external staging artifact `container-verification.json`. The record contains earlier image probes at `05d2dfc3be3a2908001a1cb9e01106e4e00cc2dd` and final rebuilds of both images at `f914f9aed9379298af43cf476d81a8cd78a7280b`. Final API build exited 0, health returned 200, and corrected application/assessment-binding files matched that commit. Final web build exited 0, home returned 200, report privacy headers passed, and missing-bearer proxy requests returned 403.

Root's recorded runtime probes additionally established API UID 10001, web UID 1000, no API `.env` in the image, report CSP, a bounded unavailable-backend response (502), and a runtime-configured web origin reaching a local stub without forwarding public-request cookies or authorization. These are reported root observations, not probes repeated by this execution agent. API container integration scope was liveness without credentials/emulators; web scope was production serving, privacy headers, unavailable state and fixed-origin stub forwarding. Full container-to-real-service integration, model calls and hosted behavior are not established by these probes. Later application or schema changes require rebuilding the affected image; image reuse does not prove new source inclusion.

## Manual deployment interface and remaining acceptance

`infra/deploy.sh` defaults to `--dry-run`. Its inputs are explicit `GCP_PROJECT`, `GCP_REGION`, `API_SERVICE`, `WEB_SERVICE`, `API_SERVICE_ACCOUNT`, `WEB_SERVICE_ACCOUNT`, digest-qualified `API_IMAGE`/`WEB_IMAGE`, and `API_ENV_FILE`/`WEB_ENV_FILE`. Runtime files are JSON objects (valid YAML), restricted to supported non-secret settings; the web file permits only `HIGHGROUND_API_ORIGIN`. The API file includes exact Scheduler audience/email/numeric subject and configurable model IDs. Hosted local bypass is forbidden.

Four required bindings use `TELEGRAM_BOT_TOKEN_SECRET`, `TELEGRAM_WEBHOOK_SECRET_SECRET`, `HASH_SALT_SECRET`, and `DEMO_OPERATOR_TOKEN_SECRET`, each containing a Secret Manager secret name plus explicit positive numeric version (`name:1` form), never the secret value. The helper creates no projects, repositories, service accounts or secrets. Deployment requires both `--execute` and `HOSTING_AUTHORIZED=true`, which must follow actual human hosting authorization. It uses explicit target project/region on each API then web Cloud Run command. Services allow unauthenticated HTTP transport for Telegram/public pages; protected API operations retain their existing application-level authentication. The helper does not alter webhook registration or Scheduler jobs; their existing helpers require separately coordinated authorized execution and verification.

No deployment, provisioning, webhook replacement or Scheduler changes ran here. Remaining hosted acceptance includes explicit billing/resource/IAM configuration, private Storage, OIDC caller verification, real webhook/Scheduler routing and the specified deployed phone journey. Hosting remains deferred; neither project existence nor local Vertex usage authorizes it.

Primary packaging references: [Docker build practices](https://docs.docker.com/build/building/best-practices/), [Cloud Run image deployment](https://cloud.google.com/run/docs/deploying), [Cloud Run secret bindings](https://cloud.google.com/run/docs/configuring/services/secrets). Registry manifest metadata was read without pulling images to establish the committed base-image digests. No hosted automation was added.
