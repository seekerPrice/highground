# Tasks20–22 — dependency and ownership execution plan

The local Must gate passed at5be7f18; Tasks18/19 are accepted at1646ebc. Tasks20–22 implementation, corrections and independent reviews are complete. Actual locked local-runtime checks passed after the preserved-data migration; final25infra/629API/33frontend and primary browser checks passed, with local acceptance recorded in tasks-20-22-verification.md. The slice breakdown below is historical execution planning, not current work assignments or a separate acceptance claim.

## Task20 first disjoint slice

Prerequisites12/13/15 are locally accepted. Begin only new `api/waste_models.py`, `api/waste.py` and `api/tests/test_waste.py`; no change to loss agent, report DTO/storage/routes, media, main, config, frontend or catalogs during policy integration.

- Define a versioned, bounded waste assessment bound to the existing inventory ID and selected assessment media ID. Item IDs must match the frozen baseline/loss items. Known damaged/destroyed items can receive the source disposition enum, finite nonnegative volume/weight estimates and explicit uncertainty/contact facts; missing/unassessed items keep unknown quantities. No free-form safety advice.
- Pure validation takes the existing frozen baseline and validated LossAssessment as inputs. Never change loss amounts or reinterpret missing stock as destroyed. Apply the fixed contaminated-food warning and reject contradictory salvage eligibility. A salvage classification is not a safety certification.
- Donation eligibility is a deterministic predicate only in this slice: assessed salvageable item, no contamination/uncertainty, separate explicit owner opt-in required. Actual owner authorization and durable donation flags remain a later integration seam; bearer capability alone never grants this authority.
- Pure aggregation consumes completed, attributed rows; use the latest completed assessment per shop/episode/inventory. Group by owner-confirmed street or Unassigned. Synthetic public output excludes private identities, exact report points and contacts. Include item/shop assessment coverage and unknown volume/weight counts; no unknown-as-zero.
- Estimated load-equivalents divide quantified volume by a validated positive capacity (proposed application default10m³ from the existing brief). Label estimates; no required-truck or guaranteed collection claim.
- Tests: identity/clip mismatch, duplicates, NaN/negative bounds, missing/unassessed quantities, contaminated-food override, uncertain donation rejection, opt-in distinction, repeated-report deduplication, episode boundaries, unknown coverage, synthetic filtering and capacity boundaries. Observe RED before new guard implementation. No external SDK/model/runtime needed.
- Done for this slice means typed pure contract and focused tests reviewed, not Task20 accepted. Freeze the contract before later Pro wire-schema/prompt, report compatibility, owner donation route and frontend integration. Old reports remain not-assessed; never silently recompute them.

## Task21 next independent slice

Prerequisites3/8/9 are locally accepted. New `api/public_check.py`, optional `api/public_check_models.py` and focused tests can follow once a lane is free. Reuse existing distance, SourceResult/Warning and destination types. Do not edit shared Telegram/main/catalog files concurrently with policy.

- Separate public sanitized results from private reader inputs. A result exposes only rounded distance, source, observation time and hazard level, plus sourced public destination listings and availability disclaimers. Hide shop identities, exact private report points and evidence IDs/URLs.
- The sender-bound intent expires after5minutes; one lookup per30seconds. Hash sender identity. Keep exact submitted coordinates transient; do not write them to analytics or public rows. Retry the same operation idempotently.
- Current-warning reader is an explicit new seam: existing source watermarks do not retain every current geographic observation, and district-only warnings lack verified geometry. Prefer existing bounded official fetch/parser results for current observations plus confirmed non-rejected private reports in their30-minute window. Reject stale/future/demo records; keep official freshness configurable. Do not claim district warnings are within2km without geometry; disclose relevant unmapped availability separately.
- Filter exact distance before rounding for output. Missing/unavailable observations never imply no flood. Resolve public destination listings through the existing bounded lookup; current opening remains unknown.
- Later configured-Flash summary consumes only sanitized canonical facts and uses validated constrained wording/fallback. Danger uses existing fixed templates and bypasses optional generation. No dispatch, risk mutation, signup, historical water-depth or open-shop feature.
- Tests cover2km boundary, times, intent expiry/replay/rate, no private leakage, unavailable/district-only states, ambiguous sender routing and Danger override. Official SDK/source behavior not already demonstrated is an implementation probe, not an assumption. Actual unregistered-chat lookup remains a root-owned acceptance step.

## Task22 last integration-sensitive slice

Prerequisites7/10/15 are accepted, but dispatch/radius and shared feedback integration serialize after current work. New `api/outcomes.py`, `api/calibration.py` and focused pure tests may be prepared independently; no trigger, calibration application or schema mutation until its contract review.

- Outcome identity is owner/shop/episode; first immutable owner response wins. Missing responses remain unknown. Due after6hours or explicit episode closure; active Danger defers non-template requests. Keep accepted real, synthetic and virtual delivery provenance distinct.
- Use source0.3 shrink threshold, at least5 responses, fresh disjoint batches in30days and10% steps bounded0.5–1.5x. Apply only non-official Warning targeting; never official coverage, Danger or fixed500m report corroboration. Calibration application is idempotent per evidence batch.
- Growth requires owner-declared indoor flooding matched to a confirmed episode with no earlier accepted alert. An alert-only callback cannot establish missed-alert cases; define its separate authenticated intake before integration. Do not fabricate false negatives from silence.
- Record response coverage and water-report counts, not unqualified accuracy. Tests cover first response, unknowns, threshold edges, batch reuse, clamps, episode/time matching, official/Danger invariance and demo isolation. Verify exact geohash implementation against primary documentation/test vectors before choosing a dependency.
- Later protected bounded due/resume jobs are manually invoked locally; no cloud scheduler or CI is authorized. Actual callback/outbox/analytics and dashboard behavior require their own review and acceptance.

## Ownership and checkpoint boundaries

Root owns runtime, SDK/model windows, Git and publication. Astra owns source/brief review and correction coordination. Sol recovery owns current Task20 shared backend/model/report integration. Sol task1 completed frozen Task21 domain and Task20 frontend candidates and now owns disjoint Task22 pure logic/tests. No simultaneous edits to shared routes/catalogs/config or frontend lockfiles. Task22 shared integration waits for explicit handoff after Task21 hooks.

The final Tasks20–22 review baseline is1646ebc. Each task retains separate actual acceptance evidence even if a coherent full local gate/review covers the milestone. Hosting and Stretch remain excluded.
