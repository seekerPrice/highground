# Synthetic media fixtures

These files are invented scenes generated with Codex's built-in image-generation tool on 13 October 2026. They depict no real shop, flood, owner, loss or insurance claim. Each image visibly says `SYNTHETIC DEMO`. Use only with explicitly synthetic demo shops and simulation events.

| File | Intended use |
| --- | --- |
| `synthetic-before.png` | Fictional baseline scene: four rice cartons, six water cases and three rice cookers, with other packaged goods on higher shelves. |
| `synthetic-after.png` | Matching fictional scene with a receded-water mark, wet muddy floor, damaged lower cartons and one tipped cooker. |
| `synthetic-before-still.mp4` | Thirty seconds repeating the before PNG; synthetic still-derived video, not walkthrough footage. |
| `synthetic-after-still.mp4` | Thirty seconds repeating the after PNG; synthetic still-derived video, not walkthrough footage. |

Visual item counts describe the generation brief, not model-verified inventory or real quantities. These fixtures exercise ingestion, hashing, schema validation and report presentation. They cannot establish real-shop recognition, valuation or damage-assessment accuracy. A matching hash establishes byte integrity only. The apparent water mark is an illustration, not a measured depth.

## Generation record

Mode: built-in `image_gen.imagegen`; opaque PNG output, no transparent background. The after image was edited from the before image after visual inspection. The generated originals remain in the Codex output directory; these copies preserve their bytes.

Baseline generation brief: a realistic modest fictional Malaysian mini-market with four `RICE 10KG` cartons in a two-by-two arrangement at left, six water cases in two stacks of three at centre, three rice cookers on the low right shelf, and generic packaged food on higher shelves. No people, real business names or prices. A prominent banner reads `SYNTHETIC DEMO — BEFORE`.

After-image editing brief: preserve the exact camera, architecture, shelves, doorway, countertop, package positions and lighting. Change the banner to `SYNTHETIC DEMO — AFTER`. Show a thin muddy wet floor after water receded and an approximately 50 cm dirty water line on walls and boxes. Keep the four rice cartons, making the lower ones sodden and sagging; keep six water cases with mud on the lower cases; tip one of the three cookers onto the floor and leave two on the low shelf. Keep higher food dry. Add no people, injuries, new stock, business names or prices. Retain prominent synthetic attribution.

The prompts are recorded as generation briefs. Do not treat the depicted goods as a pre-entered application inventory: a model result must still pass the normal schema and uncertainty checks.

## Review

Both rendered outputs were visually inspected: the labels are readable, the before/after arrangement is consistent, and no people are shown. Use the separate demo-scene prompt branch when assessing these images; do not weaken real-upload validation to accept synthetic fixtures.

The MP4s were generated locally with FFmpeg from these exact source PNGs (H.264, 1536×1024, yuv420p, 10 fps, no audio, 30 seconds). They add no visual evidence or motion. `ffprobe` verified both durations and codecs; the before clip is 899,251 bytes and the after clip is 1,068,253 bytes, each below the standard Telegram Bot API download limit. They exist to exercise video MIME, download, original-byte preservation and model/report plumbing. They cannot validate temporal video understanding.

To reproduce a clip locally, replace `before` with `after` for the second image:

```sh
ffmpeg -hide_banner -loglevel error -loop 1 -framerate 10 \
  -i demo/media/synthetic-before.png -t 30 -c:v libx264 \
  -preset medium -tune stillimage -crf 26 -pix_fmt yuv420p \
  -movflags +faststart -an demo/media/synthetic-before-still.mp4
```

FFmpeg is a fixture-authoring tool only; the application must preserve Telegram-downloaded original bytes and must not silently transcode user media.
