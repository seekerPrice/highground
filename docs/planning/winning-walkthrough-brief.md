# Winning blind spot: an inspectable first visit

Issue [#31](https://github.com/seekerPrice/highground/issues/31).

Baseline: `6c71dc456453e3c20a56247e4daa56a0a79312a1` on `task-20-21-waste-check`. User requests finding and implementing a new blind spot to improve winning chances. Astra coordinates Sol; root owns runtime, browser, full gate and publication. No hosting, CI, new sends or provider calls.

## Ranked findings and chosen response

1. Deployment remains a submission gate, but hosting authorization is still deferred; do not disguise local acceptance.
2. **Chosen actionable gap:** a first-time judge sees empty current action counts and unavailable official sources; meaningful interaction needs an operator token, while the report is private. Prior runbooks and isolated composite previews help the presenter but do not give a stranger an independently inspectable product journey. Build a public read-only worked example reachable from the dashboard, independent of live services or credentials.
3. The private comparison has noninteractive timestamps; useful later, but helping a judge reach evidence is the higher priority. Do not add timestamp-seeking this pass.
4. Real-shop valuation, native-language review and human testing remain external evidence gaps. Do not manufacture them.

The official [FAQ](https://aibuildercup.com/Faqs.html), checked 13 October 2026, assigns 40% technical/GenAI, 25% impact, 25% innovation, 10% UX and asks for an end-to-end deployed prototype, public repository, deck and video under three minutes. [Google video understanding documentation](https://ai.google.dev/gemini-api/docs/video-understanding) describes extraction and timestamp references. Our inference: exposing concrete visual inputs and captured structured outputs is stronger evidence of GenAI contribution than another architecture diagram. This is not a prediction of a score or winning guarantee.

## Implementation contract

Create `/example`: public, read-only, four linked stages that work without runtime services, credentials or API calls. Use existing design tokens and semantic links/details; responsive desktop/390/320px, keyboard focus, readable tables. Prominent dashboard entry and return link. Do not displace the map with a new hero.

- **Inputs:** reuse exact committed synthetic before/after PNG bytes as public assets. Label AI-generated illustrations and source of 30-second repeated-still videos; no real-shop, motion or temporal-understanding claim. Cite demo/media/README.md provenance in the source documentation.
- **AI estimates:** a narrow typed allowlist derived from `api/tests/fixtures/waste-journey-response.json`, which retains actual captured model output. Show six item estimates, model confidence explicitly not accuracy, and quantity uncertainty. The generation brief describes four rice cartons/six water cases while the captured model estimated six/eight; expose this discrepancy as a reason human review matters, not a passed accuracy test. Do not silently correct the captured output or invent human confirmation.
- **Deterministic action:** demonstrate existing lift-first calculation from captured baseline, floor/low only, estimated value divided by effort; top four total estimated RM850. Distinguish calculation from AI extraction. Vehicle15/stock30 minute action targets may be explanatory examples only, not actual sent alerts or flood forecasts. Explain fixed Danger bypass without rendering altered Danger messages or simulating an actual outage. No action-confirmation controls/counters.
- **Recovery:** captured estimated loss RM850 of baseline RM1700, six assessed groups; optional compact captured waste coverage (four classified, two unaffected unknown quantities) if this helps coherence. These are estimates from synthetic imagery, not avoided loss or a collection/safety commitment. Display independently calculated hashes of the exact public PNG source bytes as downloadable-file receipts, with an explicit limitation: these are public fixture file checksums, not private upload-ledger verification or authenticity proof. No fake green verification badge or private report reuse.

Use an independently typed curated public fixture containing only names/quantities/values/heights/effort/conditions/confidence/uncertainty plus public asset paths/hashes/provenance. No report/media/inventory/recipient identifiers, capability fragments, origin timestamps, private locations, donation URLs, GCS paths, or raw agent traces. Never import full private report DTO or raw captured fixture into the browser bundle. Show recorded-output versus deterministic-computation labels at each stage. No model ID is asserted: current configuration is not historical provenance. No fresh model call. Static page must not poll data, mutate state outside its own navigation, or imply current global scenario activity. Prefer server-rendered content and anchors over unnecessary state.

## Verification and review

Sol implements and runs relevant local web checks; Astra inspects actual diff and correctness. Meaningful tests bind curated facts to allowed captured source fields, deterministic rank/aggregate to existing expected behavior and fixture checksums/public privacy shape; do not test CSS strings. Root browser checks first visit with backend unavailable, stage links/keyboard, desktop/mobile overflow and asset loading. Root runs full gate. Independent Matt Standards and Spec reviews compare recorded baseline with actual working delta; correct and recheck both independently. No Git writes by Astra/Sol. Root owns reviewable publication.
