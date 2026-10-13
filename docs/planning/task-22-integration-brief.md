# Task22 — outcomes and constrained calibration

Baseline1646ebc for the Tasks20–22 review. Astra read GitHub issue23 and its empty comment list, source R3 and approved amendments. This brief is preparation; dispatch follows available ownership after Task20/21 interfaces settle. Local only, no CI/cloud scheduler or hosting. Existing local Must and18/19 checkpoints are accepted.

## Contract and proposed files

Start disjoint `api/outcome_models.py`, `api/outcomes.py`, `api/calibration.py` and focused tests; add `outcome_store.py` only for actual durable behavior. Shared dispatch, Telegram, jobs, config, analytics schemas and dashboard changes require named handoff. Root owns runtime/model/SDK windows, Git and final gate; Astra reviews and sends defects back to Sol.

- Canonical outcome key is shop plus confirmed flood episode. First authenticated current-owner response wins immutably: no, street_only, entrance, inside; optional bounded depth is separate and never inferred. Workers, bearer reports and arbitrary episode IDs grant no feedback authority. Missing response is unknown, not no water.
- Freeze episode, area, source, demo generation and earliest accepted alert facts before asking. Aggregate distinct shops/episodes rather than recipients or duplicate messages. Keep Telegram accepted, virtual delivery, failed/uncertain delivery and no prior alert distinct.
- A bounded due scanner uses configurable `OUTCOME_ASK_AFTER_H` (default6) and selects prompts six hours after the first accepted Warning/Danger alert, or immediately when the confirmed episode explicitly closes, whichever applies first. This follows source R3’s “6 hours after each warning/danger alert (or when the event closes)”; closure does not start another six-hour delay. Recheck current ownership, scenario generation and active Danger immediately before transport. Active Danger defers the non-template outcome prompt. Use durable prompt IDs/leases and the established uncertain-send semantics; replay must not send another prompt or replace a first response.
- A separate explicit owner flow can record an inside report for a confirmed episode without an earlier accepted alert; alert-only callbacks cannot establish missed-alert cases. Validate episode and observation-time ordering against stored facts, rather than trusting client claims. No current-danger media or property prompt is introduced.
- Publish water-report counts and response coverage with denominators: eligible shop/episodes, accepted prompts, responses by answer, missing/unknown. These are owner reports, not accuracy or independent water verification. Public dashboard remains synthetic-only and excludes sender/precise location/evidence data.

## Calibration rule

- Use geohash6 from confirmed shop location; never a model-generated area. A tiny typed pure encoder may avoid a new dependency, verified against primary-source vectors: longitude−126/latitude48 → `c0w3hf` ([PostGIS](https://postgis.net/docs/manual-dev/en/ST_GeoHash.html)); latitude52.205/longitude0.119 → `u120fx` ([author reference](https://www.movable-type.co.uk/scripts/js/latlon-geohash/docs/Geohash.html)). Test longitude/latitude order, equator/antimeridian/poles and invalid/nonfinite bounds.
- Only **non-official Warning targeting** uses the multiplier. Official JPS/MET coverage, every Danger event, fixed500m corroboration and `/check`2km remain unchanged. Do not implement the source's old min_level_to_alert adjustment; approved amendments permit radius only.
- Use new disjoint batches of eligible first responses within30days. With at least five responses, shrink10% when the source threshold water-response ratio is strictly below0.3. No-response cases are excluded from that response ratio and shown separately. Record consumed response identities transactionally so repeated jobs cannot reuse a batch.
- Grow10% only from a fresh owner-declared inside result matched to a confirmed episode and proven to have no earlier accepted alert. Consume that evidence once; never infer a missed flood from silence, virtual transport, failed prompt or later changed answers. An earlier sending/uncertain delivery or incomplete/overflowed history is unknown, not proof that no alert was accepted; suppress growth in those cases. Area and time eligibility come from stored confirmed episode facts.
- Clamp0.5–1.5, preserve original radius and freeze applied multiplier/evidence version with the target plan. Real and synthetic calibration state is isolated; reset generation cannot replay old demo learning. Persist an auditable reason, counts/window and old/new multiplier without exposing private identities.

## Integration sequence

1. Freeze typed outcome, due-prompt, response-coverage and calibration decision contracts with pure RED/GREEN tests.
2. Add atomic first-response/batch-consumption stores and outboxes; run isolated real Firestore tests in a root-approved window. Derive due timing from existing accepted alert/risk records; do not invent closure from stale/missing sources.
3. After Task20/21 shared handoff, integrate owner commands/callbacks and a protected bounded due/resume job. Reuse exact scheduler/operator authentication and fixed Danger guards. Local invocation and any local recurring runner must be documented honestly; no claim that a manual job is automatic cloud scheduling.
4. Add typed analytics rows using the existing bounded BigQuery sink/query helper. Prefer a dedicated outcome fact table if mutable per-recipient alert rows would violate first-owner/episode identity; document how it projects the source's `alerts.outcome` intent. Root initializes/migrates only approved local resources non-destructively.
5. Apply the frozen multiplier at non-official Warning target selection only. Preserve dispatch idempotency, current-generation checks and all authoritative-source invariants. No model is needed to calculate the rule.
6. Hand the frozen public DTO to the single frontend owner for counts/coverage/trend and labelled synthetic history. Keep existing metrics definitions, unknown states, privacy headers and report/PDF behavior unchanged.

## Behavioral verification and done

Tests must cover first-owner response under concurrency; worker/other-shop/cross-episode rejection; six-hour and closure boundaries; active-Danger escalation just before send; lost/uncertain transport; restart/outbox replay; missing responses; duplicate recipients; accepted-versus-virtual provenance; new disjoint batches; exact0.3/five-response/window edges; 10% clamps; single-consumption growth and prior-alert ordering; official/Danger/corroboration/check invariance; scenario reset; private-field exclusion. Actual local job/callback/analytics/UI evidence is separate from pure tests.

Done only when root demonstrates the protected due workflow and synthetic outcome/calibration journey against real local service clients, required local gate passes, Astra corrections are rechecked and independent Matt Standards/Spec return no unresolved findings. No real-world forecasting improvement or cloud-deployment claim follows from seeded history.
