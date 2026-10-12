# Task 4 local Telegram webhook

Requires the installed backend lock and the existing loopback Firestore emulator. Run from the repository root:

```sh
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 .venv/bin/python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 .venv/bin/python -m pytest api/tests/test_telegram_webhook.py -q
```

Settings load the ignored root .env with environment variables taking precedence. The typed operator_token attribute reads DEMO_OPERATOR_TOKEN, matching the example configuration. Never shell-source .env. Health works without credentials; webhook needs project, token and secret. No real outbound send occurs in tests: transport is injected. Persistent inbox tests use the actual emulator, own project/unique collection names and delete only their own documents. Restarting the app preserves inbox state in the running emulator; restarting the emulator clears its temporary data.

When root provides and authorizes an explicit public HTTPS tunnel URL, root can run:

```sh
./infra/set_webhook.sh https://actual-public-tunnel/telegram/webhook
```

The script loads secrets within Python, submits setWebhook without secret CLI arguments and verifies getWebhookInfo's URL. It does not create a tunnel, deploy a service, drop queued updates or print private API errors. Successful registration does not establish callback delivery: root must send /start and verify the real bot reply separately. No real webhook mutation has been performed by this implementation lane.

Local verification: 20 focused health/webhook tests passed against the actual loopback emulator without warnings; authentication, dedupe and log-redaction tests each failed when their implementation was deliberately disabled, then passed after restoration. Shell syntax passed; an HTTP URL was rejected without Bot API calls. The running API returned HTTP200 health and HTTP403 for an unauthenticated webhook.

The endpoint checks the secret header before parsing, validates integer update IDs and handles only private /start; unsupported validated updates are durably recorded and acknowledged. State transitions are processing → sending → done; definite Bot API rejection permits retry, ambiguous network/response failures become uncertain and are not automatically resent. Concurrent claims use Firestore transactions. A crashed sending lease becomes uncertain when redelivered. A crash before sending can reclaim an expired processing lease. This avoids blind duplicate sends but cannot promise exactly-once external delivery; uncertain records require later operator reconciliation. Telegram acceptance does not prove the recipient read a message.

Inbox records retain only claim/deduplication metadata and processing outcomes. Raw update payloads, private text, contacts and sender/chat details are not persisted. A public webhook regression verifies the exact metadata-only record for an unsupported private update. Existing local records were not migrated or deleted; root must assess any earlier local records separately. Token-bearing URLs and raw payloads are suppressed from responses/errors. [Telegram webhook secret and retry semantics](https://core.telegram.org/bots/api#setwebhook), [update IDs](https://core.telegram.org/bots/api#update), [Firestore transactions](https://docs.cloud.google.com/firestore/native/docs/manage-data/transactions).
