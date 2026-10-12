# Parallel Tasks 4 and 6 — local foundation

Authorized by the all-task/local-first instruction. Task 2/3 local review corrections precede this work; independent Matt review covers the coherent 2–6 foundation before any completion claim. Baseline 142178f. No hosted deployment or resource provisioning.

## Shared contracts and ownership

Task 4 owns api/config.py, api/main.py, api/tools/telegram.py, Telegram webhook/inbox modules and tests, infra/set_webhook.sh and local run instructions. Task 6 owns api/agents/, api/tools/gemini.py, api/tools/firestore.py, ADK/session tests, local fake-warning runner, and backend dependency declarations/lock. Do not edit api/models.py without coordinating with Astra. Task 6 adds the small shared runtime dependencies required by both lanes. Send interface changes promptly.

Configuration uses python-dotenv for the ignored root .env and environment overrides; never shell-source it or print its contents. Task 4 provides a typed Settings object with gcp_project, telegram_bot_token, telegram_webhook_secret, hash_salt, operator_token, vertex_location, gemini_fast_model, gemini_pro_model; secrets excluded from repr. Empty model IDs remain configurable and fail clearly only when model operations are requested. Health remains independent. Emulator host is process configuration honored by the Firestore SDK.

Task 6 provides create_firestore_client(settings) in api/tools/firestore.py: configured project; anonymous emulator credentials when emulator host is set, otherwise ADC with explicit HighGround quota project. Do not modify global ADC or use an unrelated CLI project. Root has a real loopback Firestore emulator at 127.0.0.1:8787. Tests use their own isolated collection/project identifiers and only clean their own data.

## Task 4 — Telegram webhook

Deliver /telegram/webhook with constant-time secret-header check, validated update identifier/body, durable Firestore inbox/claim state, restart-safe dedupe and minimal /start greeting. No onboarding implementation yet. Use raw Bot API over existing httpx; never log token-bearing URLs or private update bodies. Inject transport/store boundaries for meaningful tests. Acknowledge only after durable processing state; do not launch untracked post-response work. Be honest that an ambiguous external send failure cannot be made exactly-once by local state alone.

Expose an app factory/lifespan as needed while retaining /healthz unchanged. Telegram service should be a cohesive handler with a store and API transport, not speculative plugin layers. The local set_webhook script requires explicit HTTPS public tunnel URL and configured secret/token, submits parameters without putting token values in shell command arguments/logs, verifies getWebhookInfo and does not create tunnels through guessed services. Root owns actual Telegram account interactions and will coordinate the real callback once local endpoint is ready.

Tests: wrong/missing secret rejected without work, valid /start reply via injected Bot API transport, duplicate update sends once across handler reconstruction, concurrent duplicate claim, malformed/unsupported update does not crash or disclose secrets, failures retain retryable/uncertain status. Use the real emulator for persistence/reconstruction tests. Record live bot webhook acceptance separately from local transport tests.

## Task 6 — ADK and Gemini foundation

Use actual google-adk 2.11.0 and google-genai 2.29.0 (verified official packages), google-cloud-firestore 2.34.1 and required compatible runtime dependencies, pinned and locked. Read docs/planning/adk-runtime-research.md and local-environment.md. ADK ships google.adk.integrations.firestore.firestore_session_service.FirestoreSessionService; inspect/smoke the actual import before writing anything custom. Use configured collection namespace and Firestore client.

Implement root highground_coordinator with triage_agent, alert_agent and loss_agent. Stub tools may return explicit unavailable/not-implemented results as Task 6 requests; they must never send alerts or claim future features work. Deterministic triage/tool boundaries remain clear. Use typed structured inputs/outputs and actual ADK runner/session API, with session state keyed to a stable hashed Telegram identity when integrated later. Avoid an in-memory production session fallback.

Gemini helper uses Vertex mode, configured project/location/model IDs, explicit quota-project ADC, async client, Pydantic response schema, finite token/time limits and one bounded retry for invalid schema/transient failure. Root verified both configured models with 1024 output tokens and low thinking. Do not hard-code those model IDs. Photo/video capabilities are future slices, but shared helper should not make speculative guesses about them.

Provide a small local runner for a simulated warning with inspectable agent decisions; no real alerts. Tests: root/sub-agent structure, actual Firestore session create/append/reload across service reconstruction, schema failure/timeout retry semantics with injected client, and one real configured Vertex structured-output smoke using the provided local environment. Credentials remain private, tests do not print responses containing personal data. Live smoke may be an explicit command rather than automatic unit suite network work.

## Done and pitfalls

Each lane reports changed files, exact local commands/results, limitations and no-cloud status. Astra reviews actual implementation, directs corrections and reruns affected checks. Independent Matt Standards/Spec review follows the foundation candidate. No task is closed solely because files exist. Shared dependency resolution/config contract and emulator namespaces must be coordinated, not raced. Do not provision Run/Storage/PubSub/BQ resources or reset the emulator wholesale.
