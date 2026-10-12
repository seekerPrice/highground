# Task 5 — live local Telegram evidence

13 October 2026 MYT. This checks a real Telegram account against the local API through the existing temporary ngrok tunnel. It is not Cloud Run acceptance or a two-phone worker test.

## Observed journey

1. `/start` displayed the eight language choices; English was selected from the actual reply keyboard.
2. `/address Pasar Moden Sri Muda, Shah Alam, Malaysia` called the configured public Nominatim service and returned a Telegram map venue with an explicit confirmation choice.
3. Confirmed the public test location, entered `Synthetic Demo Shop`, selected mini-market, ground floor, vehicle present and van, and skipped the optional worker invitation.
4. The bot visibly replied with registration complete and provisional score60/100, explicitly leaving inventory value and river/past-flood exposure unknown.
5. Firestore inspection verified exactly one matching new shop, one English owner recipient, the expected details and provisional score. Normal registration set `is_demo=false` even though the name contained “Synthetic Demo”.
6. Root then marked only this newly created local synthetic fixture as `is_demo=true`, with an explicit fixture-origin note, for subsequent simulation tests. The operation asserted loopback emulator, project, creation time, exact name/type/vehicle, public address and one recipient before changing that flag. No public enrollment endpoint or name-based auto-demo rule was introduced.

Telegram webhook configuration was refreshed to accept `message` and `callback_query`, with no pending updates or delivery error at the checked point. The Chrome Telegram view briefly failed to display one accepted reply; refreshing recovered it. The backend recorded successful sends and returned no processing error during registration. Telegram's browser network-status label remained stale while messages and replies continued to arrive.

## Proof and limits

The locally saved screenshot `/Users/lucaslt/.codex/outputs/highground/setup/telegram-onboarding-pass.png` shows the completed synthetic conversation, cropped to the HighGround chat to exclude unrelated private chats. It was visually checked and shown to the user. Private chat identifiers and tokens are omitted from this document and the public repository.

This fixture is an invented shop at a public facility coordinate, not a claim that a business there enrolled. Worker consent, independent native-language review and two real consenting phone testers remain separate acceptance evidence. This live flow complements the focused automated tests; it does not replace Astra's corrections or independent Matt reviews.
