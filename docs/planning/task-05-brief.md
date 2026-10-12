# Task 5 — eight-language onboarding

Authorized under the all-task, local-first instruction. Task 4's durable inbox and Task 6's pinned runtime are the foundation. No hosting, Shoulds, or Stretch. Preserve the original source and approved amendments.

## Ownership and interfaces

The Telegram Sol lane owns onboarding modules/tests, `api/i18n/`, one-off translation script, and integration into the existing webhook/transport. Keep the durable inbox and secret checks intact. Coordinate shared settings, models and dependency changes with Astra; do not race the other lane's lockfiles. Domain persistence uses the existing Firestore SDK and local emulator. Keep public shop serialization separate from private recipient records.

Implement deterministic, restart-safe conversation stages: language, location/address candidate confirmation, shop name/type, floor, vehicle/type, optional consenting worker, save and risk summary. Accept all eight specified language codes. Reject malformed locations and bounded invalid user inputs with a useful retry prompt. Do not let model output control onboarding state or authorization.

The shop shape follows Section 8. Expose a clear store boundary for later dispatch to read location, floor, vehicle, recipients and inventory summary. Use stable salted identity for private conversation records. Persist progress and final shop idempotently across repeated Telegram updates; no duplicate shops or workers. The bot's `/start` can resume or explain an existing registration rather than silently overwrite it.

## Consent, location and score

A worker must self-start the bot and explicitly join via an expiring, single-use random invitation, choosing their own language. Never accept an arbitrary worker chat ID from the owner. Keep invitation tokens private and hashed at rest. Owner may skip this step. Worker consent must be bound to the intended shop; replay/expired tokens fail clearly.

Shared location is preferred. Address geocoding must return a candidate and require explicit user confirmation before saving coordinates; no guessed location. Research the official provider usage requirements, use a bounded request and identifiable user agent, and handle no/ambiguous results. If provider access fails, offer location sharing. Do not build a new geocoding infrastructure.

Risk score uses Section 9 only. Ground-floor and vehicle components can be calculated now. Missing inventory and sourced river/past-event exposure are unknown/uncredited, never silently treated as proof of low risk. Explain the provisional score and recompute when later data exists. No safety guarantee.

## Language and Danger contract

Author English static strings and fixed Danger variants; generate the other seven once using the configured Vertex helper and strict schema, commit them with `_reviewed: false`. Preserve key/placeholder parity. Never translate Danger at runtime. Include the required emergency footer in the fixed template and a fixed no-destination variant. Only approved destination name/link placeholders are permitted; no generated advice or deadline in Danger. Use sourced-destination wording without implying availability or route safety. Native-speaker review remains explicitly pending.

The one-off generator must not overwrite reviewed files silently or expose secrets; validate generated keys, placeholders and language metadata before writing. Runtime loading fails clearly for missing/malformed files, with a documented English fallback for unsupported language codes only. Dynamic alerts belong to Task 7.

## Verification and done

Exercise the public webhook through a complete owner flow, invalid input and restart mid-flow against the isolated Firestore emulator. Verify duplicate completion creates one shop; worker consent, expiry and replay; geocoder failure/candidate confirmation; provisional risk calculation; all eight language files and exact Danger placeholder parity. Use mocked external transport for repeatable tests and one explicit real model generation run for committed translations. Do not send unsolicited live messages.

Record commands/results and limitations. Astra inspects actual files, returns defects and rechecks; independent Matt review follows a stable candidate. Local onboarding acceptance does not establish deployed bot acceptance or native translation review.
