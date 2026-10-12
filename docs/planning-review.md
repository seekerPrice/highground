# HighGround planning review

Reviewed 13 October 2026. Planning only; no implementation started.

## Authority and workflow

Read the complete handover files `01-build-spec.md` (source of truth), `00-README.md`, and `03-zhaowei-tasks.md` (context only). Current user instructions override conflicting handover wording.

Wait for **Task 1**. For each subsequent Section 12 task, Astra coordinates: plan that task, direct Sol to implement it, inspect the actual changes and test results, send defects back to Sol, and recheck corrections before reporting completion. Do not jump ahead or begin the next task until the user confirms.

Fixed constraints: Section 5 stack; all Musts deployed Thursday 15 October; Shoulds only Friday after Tasks 1–17 work on deployed URLs; Stretch pitch-only; fixed Danger templates; no safety/authenticity guarantees; vehicle deadline strictly before stock; secrets in environment/Secret Manager; configurable model IDs; no GitHub workflows, Dependabot, other GitHub automation, or repository-connected Cloud Build triggers.

## Product in five lines

1. Telegram flood copilot for Malaysian shops, demonstrated in Taman Sri Muda.
2. Video inventory produces estimated stock values and a deterministic lift-first ranking.
3. Official warnings and nearby reports produce multilingual action alerts and sourced destination links.
4. Danger bypasses generated text and uses committed fixed language templates.
5. Recorded upload hashes support estimated loss reports; a dashboard shows alerts and self-reported protective actions.

## Primary-source checks and observed blocker

The parent agent performed these live checks on 13 October 2026 and supplied the results to this planning review.

- **Flood feed is not validated as current:** [data.gov.my flood endpoint](https://api.data.gov.my/flood-warning) returned HTTP 200 and 1,276 station records. Of these, 725 had null `water_level_update_datetime`; the latest non-null value was **2024-02-23 14:45:00**, with no timezone inferred here. Indicator counts were null 712, NORMAL 514, ERROR 45, ALERT 3, and DANGER 2. Old DANGER records must not trigger current warnings. Availability of an HTTP endpoint is not evidence of fresh observations.
- The feed's `water_level_indicator` carries level categories; `water_level_status` contains ON/OFF device status. An inspected record had non-monotonic thresholds (normal 133.4, alert 133.93, warning 133.33, danger 135). Validate semantics and malformed measurements; do not derive severity by blindly sorting these thresholds. Capture fixtures in Task 3, preserve source observation times, exclude stale/error readings from live alerting, and expose unavailable/stale source status. A current official source remains unresolved; simulations must be clearly labelled.
- [Weather endpoint](https://api.data.gov.my/weather/warning) returned HTTP 200 with four warnings. The inspected first warning concerned marine winds/seas, with heavy-rain mentions and no coordinates or district IDs. Text containing “heavy rain” must not automatically become a local terrestrial flood watch. Inspect warning type, validity and geography, and define conservative district mapping using [official weather API documentation](https://developer.data.gov.my/realtime-api/weather).
- [Telegram Bot API](https://core.telegram.org/bots/api#getfile) confirms the standard hosted `getFile` download limit of 20 MB. Webhook retries after non-success responses and secret-token header verification must be accommodated. Preserve downloaded Telegram bytes for hashing; they may differ from original camera files.
- [ADK Cloud Run deployment guidance](https://adk.dev/deploy/cloud-run/) warns that in-memory sessions do not survive restarts. Durable conversation state and restart recovery are required; do not assume Firestore is a built-in ADK session adapter without checking.
- [Vertex video documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/video-understanding) is the reference for model-specific video input constraints. Actual accessible Flash/Pro model IDs, location, quotas and schema/tool compatibility still require project-specific validation. Keep names configurable.
- The [hackathon landing page](https://hack2skill.com/event/aibuildercup2026) yielded an empty JavaScript shell during inspection. Eligibility, scoring and submission rules are therefore handover claims pending accessible official rules or pasted portal content.

## Conflicts and proposed resolutions

| Issue | Resolution proposed for agreement |
|---|---|
| L5 dashboard is Must but Task 15 is Friday | Preserve numbering: complete Task 15 after Task 14 on Thursday and redeploy. Friday begins with Tasks 16–17. |
| One deadline in §6.2 versus vehicle before stock | Use two deterministic action deadlines. Define the response-window policy; do not invent a predicted road-flooding time. |
| Danger template versus universal emergency footer | Include emergency wording inside each fixed template, with only destination name/link substitutions. Use a fixed no-destination fallback. |
| Destination/route described as “safe” | Use sourced listed/designated labels and opening-status qualifications; distance and a map link do not establish safety. |
| Watch requires a Should offline card | Send a short text Watch until Task 18 is deployed; never claim a card was sent when absent. |
| Must L5 mentions Stretch water-depth dots | Keep water-depth estimation, dots and memory-map collection pitch-only; implement the other Must layers. |
| “Verified evidence” overstates hashing | Prefer “File integrity verified,” or immediately explain that matching bytes do not establish authenticity, capture time, location or loss accuracy. |
| Eight ranked items, five displayed, whole-value confirmation | Tie confirmations to an immutable inventory/item snapshot and the exact items represented by the action. Owner/worker repeats must not double count. |
| Policy deletion versus immutable originals | Task 19 needs an explicit retention exception: retain hash/ledger, delete policy originals by default, and do not claim current verification after deletion. |
| Demo/pitch promises unbuilt features | Label absent Shoulds/Stretch as next. Only a previously saved card works offline. |

## Three principal risks

1. **Misleading safety decisions.** Stale official readings, marine text, model confidence, proximity and route links can all be mistaken for reliable local guidance. Mitigate with deterministic validated triage, freshness and geographic checks, fixed Danger/fallback templates, and explicit uncertainty. Reject unrelated media before applying the “unverified report” rule.
2. **Lost or duplicated processing.** Telegram retries, slow video analysis, Cloud Run restarts and repeated buttons can duplicate sends/counters or partially write media/ledger state. Persist state, deduplicate updates and event-recipient dispatches, make confirmations transactional, track resumable processing stages, and use the existing Pub/Sub service for durable work where needed. A webhook acknowledgement followed by untracked background work is insufficient.
3. **Too many late integrations.** ADK, Vertex access, real feeds, media handling and destinations may fail just before the first deployment. Validate each dependency when its foundation task arrives, preserve Thursday deployment, and allocate Friday to demo/hardening before Shoulds.

## Decisions still needed

- GCP project, billing/access, repository destination, Telegram bot, two real testers and accessible Vertex models.
- Sourced destination coordinates, source dates, verification meaning and current/unknown opening status; fixed behaviour when no credible destination exists.
- River proximity data is absent. Shop district is missing although MET matching requires it. Initial risk score precedes inventory and must later be recomputed; unknown inputs must not be presented as assessed.
- Worker recipients require explicit opt-in and a reachable Telegram account linked to the correct shop.
- Public demo/reset access and exposure of real shop coordinates, reports and evidence need a defined policy. Unguessable report links are bearer access, not account privacy.
- Later task schemas need stable item IDs, alert value snapshots, confirmation keys, source event lifecycle/expiry, processing states, object generations and retry-safe ledger keys. Telegram accepting a send is not proof that a person received/read it.

## Four-day sequence

- Tuesday: Tasks 1–5.
- Wednesday: Tasks 6–10.
- Thursday: Tasks 11–14, then Task 15 and redeploy to include all Must dashboard features.
- Friday: Tasks 16–17, then Should Tasks 18–22 in order only if the deployed prerequisite gate passes and time remains. Stretch stays pitch-only.

This sequence is a planning proposal, not authorization to begin or combine tasks.
