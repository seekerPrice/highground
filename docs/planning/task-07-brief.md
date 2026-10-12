# Task 7 — local alert dispatch

Authorized Must implementation after the reviewed foundation. Task 5 may proceed in parallel behind explicit shop/i18n contracts; full integration acceptance requires its completed records. Do not host or provision cloud resources. No offline cards or other Should features yet.

## Ownership and boundaries

The data/ADK Sol lane owns dispatch modules, geo helpers, event/alert persistence, Pub/Sub and BigQuery clients, dispatch tests and dependency locks. The Telegram lane owns onboarding, i18n and the shared webhook/transport; coordinate required transport buttons and settings additions before editing those files. Use a separate FastAPI router; ask the entrypoint owner to include it once its contract is stable. Do not race shared models.

Use the Section 8 shop/event/alert records and Task 5's private recipients. Coordinates and radius must be finite and bounded; haversine targeting is deterministic. Recipients retain independent languages. Public output never includes their identifiers. Snapshot the exact displayed lift-first item list, estimated value, vehicle action and deadlines into each alert; later confirmations must read that immutable snapshot, not a newer inventory. Missing inventory/destination yields honest unavailable wording, no invented values.

## Behaviour

Implement operator-authenticated `/demo/simulate-warning`, requiring `DEMO_MODE` and the configured `DEMO_OPERATOR_TOKEN`. Validate watch/warning/danger, position and radius. Every simulated event and resulting alert is visibly labelled. Use durable request/event identity so retrying creation resumes pending work without a new flood event. Persist dispatch progress before external effects, record definite failures separately from uncertain delivery and never blindly resend an uncertain message.

Publish every new event through the official Pub/Sub client and append event/alert rows through the official BigQuery client. Emulator endpoints are explicit local configuration; accept anonymous credentials only for validated loopback emulator endpoints. BigQuery requires explicit ClientOptions endpoint. Cloud clients use the configured project and explicit quota project. Existing local emulator bucket/dataset/topic facts are in local-environment.md. Never label emulator success as IAM verification.

Use durable per-sink progress/outbox state so a crash between Firestore, Pub/Sub, BigQuery and Telegram does not lose the event or repeatedly send recipients messages. Keep this narrowly tied to the required sinks; no generic job framework. BigQuery streaming insert IDs are best-effort dedupe, not an exactly-once promise: retain stable logical row IDs and ensure subsequent aggregates dedupe them. Pub/Sub consumers must expect duplicate messages.

Warning composition uses configured Flash and a strict JSON schema with a bounded retry and fixed friendly fallback. The approved amendment narrows model output to selecting approved localized structure/situation keys. Use the actual coordinator/alert_agent for that useful selection, persist the ADK trace, validate the selected key and keep a short total budget. Do not add a redundant model audit after dispatch. Deterministic dispatch never requires model permission. Amounts, item names, destinations, route URLs and action targets come from validated input. Targets are configurable positive minutes, default vehicle15 and stock30 after event creation; enforce strict vehicle-before-stock ordering and label them action targets, never flood-arrival predictions. All RM values are estimates. Include the fixed emergency footer in the recipient's language.

Danger dispatch is an absolute wrapper-level bypass of model output: use only the committed language template with allowed destination placeholders or the fixed no-destination variant. Never call a model, request video, show stock/vehicle actions, or add prose at Danger. Route button only when a sourced destination exists. Templates and translation-review metadata come from Task 5. Simulation/review labels must be designed consistently with the approved fixed template, not appended ad hoc to Danger text.

Watch uses static warning text until Task 18 is permitted; do not claim an offline card exists. Destinations and vehicle confirmation handling belong to Task 8; stock confirmation belongs to Task 11. Prepare the immutable snapshot contract now without pretending those callbacks work.

## Verification and acceptance

Tests cover radius edge/outside cases, input rejection, operator/DEMO_MODE gates, recipient languages, exact Danger output with malicious model text ignored, no model call at Danger, ordered targets, empty inventory/destination fallback, duplicate event and dispatch retry, uncertain external delivery, and crash recovery for required sink stages. Use isolated Firestore/PubSub/BigQuery emulator records and actual official clients for integration checks; no real recipient sends without a consenting test account.

Wire completed deterministic domain tools into the ADK boundary where relevant; do not describe the Task 6 stubs as actual dispatch. A scripted fake can test routing, but final Must acceptance must exercise the real integrated application. Record exact local commands, meaningful results and remaining Task 8/9/10/11 integration boundaries. Astra reviews/corrects, then independent Matt axes review the stable milestone before completion claims.
