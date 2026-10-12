# ADK runtime evidence — 13 October 2026

Inspected the published [google-adk 2.11.0 package metadata](https://pypi.org/pypi/google-adk/2.11.0/json) and its Python wheel directly, before implementation. Current [session overview](https://adk.dev/sessions/session/) lists in-memory, Vertex and relational services but is not an exhaustive inventory of the wheel.

## Firestore sessions

The published wheel contains `google.adk.integrations.firestore.firestore_session_service.FirestoreSessionService`. Its constructor accepts an optional `google.cloud.firestore.AsyncClient` and `root_collection`; default root is `adk-session`. It implements create/get/list/delete and append_event. Create and append use Firestore transactions. Append compares a stored revision marker and raises StaleSessionError on an outdated session. Partial events are not persisted. Session state and event records are stored separately; app and user state have their own collections.

Use this shipped integration when Task 6 validates the installed import and behavior, rather than writing a speculative custom adapter. Production must pass an explicit project client. Tests should demonstrate persistence across two service instances and stale-write handling against the Firestore emulator or dedicated project. Inspection alone is not proof of that runtime behavior; it remains unverified until the smoke test runs. Onboarding domain records still need their own durable, idempotent application operations. Do not replay side effects blindly after a session conflict.

## Gemini schemas

The [official google-genai SDK documentation](https://googleapis.github.io/python-genai/) supports Pydantic response schemas via GenerateContentConfig and async requests via client.aio.models.generate_content. Validate the returned structured values again at the application boundary. Keep model names and Vertex location configurable; no project-specific model access has been tested yet.

Registry versions observed: google-adk 2.11.0; google-genai 2.29.0; google-cloud-firestore 2.34.1. Dependency resolution must still establish a compatible pinned environment. Application default credentials, target project and model invocation remain external checks.

## Actual emulator smoke result

The official ADK2.11.0 FirestoreSessionService was exercised against the local Firestore emulator using google-cloud-firestore2.34.1. A second service/client instance restored the first instance's state and event; appending from an older session snapshot raised StaleSessionError. The smoke deleted only its UUID-named synthetic session and confirmed removal. All three assertions passed, process exit0. This verifies the shipped adapter at that boundary; application onboarding concurrency and idempotency still require their own tests.

## Warning selector latency check

The configured Flash model's [official developer guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash) explicitly supports `LOW`, `MEDIUM` and `HIGH` thinking levels; `MINIMAL` returns a validation error. The guide also says temperature/top-k/top-p are ignored for this model. Use schema validation and constrained outputs, not a temperature setting, as the boundary on recipient-facing content. The model ID remains an environment setting.

Task 7's early real ADK selector probe received a Vertex timeout with a short HTTP limit. A successful fallback verifies resilience, not a successful model invocation. The implementation review requires a separate actual successful selector result and persisted trace, plus measured application latency; an increased diagnostic timeout must not silently increase the recipient dispatch budget. See the task verification record for final results when available.
