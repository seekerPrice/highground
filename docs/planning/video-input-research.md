# Native video input: documentation and local transport probes

Checked 2026-10-13 for the configured Vertex `gemini-3.1-pro-preview` model in `global`. Model names remain configuration values; no application model was changed. These probes use generated fictional shop imagery and prove transport/schema behavior only, not inventory accuracy, real evidence authenticity or walkthrough understanding.

## What the primary sources establish

The [current Pro model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-pro) lists video input, supported MIME types including MP4, up to ten videos and duration limits. Its 7 MB inline limit is listed under images; it does not give an equivalent video byte ceiling. Do not apply the image number to video.

The [inference reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/inference) describes base64 inline data and separate Cloud Storage/HTTP file URI paths. Its 15 MB video restriction belongs to publicly readable HTTP URLs, not the inline path. Local storage emulator URLs cannot be fetched by the remote model as private Cloud Storage objects. Google's [local-video sample](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/googlegenaisdk-textgen-with-local-video) demonstrates sending local bytes through the Gen AI SDK.

[Firebase AI Logic](https://firebase.google.com/docs/ai-logic/input-file-requirements) documents a 20 MB total request limit and base64 expansion. [Flex PayGo](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/flex-paygo) separately documents a 20 MB inline request payload limit. These are distinct documented paths; neither establishes the exact observed ceiling of our standard Vertex request. Do not change the stack, service tier or SDK because of this ambiguity.

## Observed configured-model results

A separate synthetic transport fixture was derived from the existing fictional before-video using H.264 constant-bitrate encoding. The repository's original demo files were not changed. `ffprobe` confirmed 30 seconds, H.264 and 1536×1024 pixels.

| Probe | Raw MP4 bytes | Base64 bytes before JSON/prompt | Result |
|---|---:|---:|---|
| Large local clip | 18,690,940 | 24,921,256 | Valid structured response, STOP, 11.366 seconds |
| Exact application upload boundary | 20,000,000 | 26,666,668 | Valid structured response, STOP, 10.952 seconds |

For the exact-boundary test, a valid MP4 `free` box pads a separate copy to exactly 20,000,000 bytes; `ffprobe` still reports the expected stream/duration. This deliberately checks transport bytes without claiming added visual complexity. Both calls used the configured Pro model through the actual Vertex SDK, one request each, bounded timeout, no SDK retry. The response schema requested a short scene description; it did not test the final inventory schema or ADK loss-agent integration.

The observed requests exceed 20 MB after base64 and were accepted. This disproves treating that adjacent documented total as our currently observed universal standard-path limit, but does not establish a provider guarantee for every format, future model revision, or larger aggregate request.

Keep ingestion's 20,000,000-byte bound and preserve every accepted original. Processing failures must remain explicit and recoverable; never truncate or rewrite evidence to fit a model request. Task 12 can compare frozen validated baseline inventory JSON with one after-video, so it need not send two full original videos together. Both originals remain linked as report evidence.

Operational probe script and results are in the local output directory `/Users/lucaslt/.codex/outputs/highground/setup/`: `probe_inline_video.py`, `large-inline-video-result.json` and `exact-20mb-inline-video-result.json`. They are development evidence, not production code or CI. No cloud media bucket, hosted app or repository trigger was created.
