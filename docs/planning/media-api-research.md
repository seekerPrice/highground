# Media transport checks — 13 October 2026

## Telegram boundary

The official [Bot API File/getFile documentation](https://core.telegram.org/bots/api#getfile) limits cloud Bot API downloads to 20 MB. A 30–45 second phone video can exceed this; duration alone is not an adequate guard. Check declared size and enforce an actual streamed-byte ceiling. Give a clear shorter/compressed-video retry instruction; do not silently transcode originals. Hash the exact downloaded bytes, which may already have been transformed by Telegram.

The same reference limits sendMessage text to 4096 characters after entity parsing. Bound dynamic fields and localized output before dispatch. Download URLs contain the bot credential, so never publish or log them. Use only the Bot API's validated file path under its fixed download origin; a user-supplied URL is not a media-ingestion authority.

## Gemini during local-first development

Vertex cannot fetch a `gs://` object that exists only in a loopback storage emulator. Google's [local-video Vertex SDK sample](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/googlegenaisdk-textgen-with-local-video) supports inline video bytes with `Part.from_bytes(data=..., mime_type='video/mp4')`. The [official Python SDK reference](https://googleapis.github.io/python-genai/) documents byte parts and async structured generation. Use the same SDK and configured model; no new cloud bucket or alternate model provider is required for this local path.

Observed probe: a generated two-second blue test clip (1903 bytes, H.264 MP4) was supplied inline to the configured Pro model with a Pydantic colour schema. It returned schema-valid `blue` in 2.48 seconds, exit 0. Raw evidence is outside the public repository at the local setup output directory. The probe used explicit HighGround quota credentials and bounded timeout/tokens. It contains no real shop or personal media.

This verifies that model/SDK inline video transport works. It does not prove inventory valuation, damage comparison, all supported codecs, or performance for real 30–45 second footage. Those require Task 11/12 integration tests. Enforce a conservative total request budget including base64 overhead, and preserve the stored original independently of any model-derived data. Do not assume the Telegram download limit equals the model request limit.
