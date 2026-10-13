# Completion audit after 4a992a4

The initial read-only audit checked preserved source Sections12/13 and approved amendments, current source/tests and retained operational artifacts. The earlier local acceptance is evidence, not a substitute for checking each requirement. Two independent reviewers inspected task coverage and safety/spec invariants; no SDK/model/browser operations were run by this audit. Root independently owns final packaging and tile-failure checks.

## Task mapping at the audited checkpoint

The table records the initial findings against4a992a4. Correction, final-gate and reconstructed-runtime evidence below supersede its then-pending statuses.

| Task | Actual implementation / verification anchors | Audit result |
|---|---|---|
|1 Scaffold|api/main.py health route;web/app;README;LICENSE;.env.example;test_healthz|Present|
|2 Infrastructure|infra/setup.sh andschemas;infra/tests/test_setup.py;local_setup.py|Local scripts present;cloud apply deferred|
|3 Data clients|api/tools/datagov.py;test_datagov|Parsers/dedupe/fixtures present;fresh external coverage not claimed|
|4 Webhook|telegram_webhook.py;infra/set_webhook.sh;test_telegram_webhook;actual own-chat proof|Present|
|5 Onboarding/i18n|onboarding.py;eight catalogs;test_onboarding/test_i18n;actual registration proof|Present;native-language review external|
|6 ADK|agents/coordinator.py;runtime agents;test_adk/inventory_adk;actual Vertex/session proofs|Actual model/agent paths present;stubs not mistaken for all runtime work|
|7 Dispatch|dispatch.py;alert_composer.py;test_dispatch/emulators;actual Warning/Danger proof|Present;destination-read outage gap below|
|8 Places/vehicle|destinations.py;vehicle_confirmations.py;seed_safe_points.py;actual duplicate callback|Present;source/opening qualifications maintained|
|9 Media/photo|media.py;photos.py;photo agent;test_media/photos;actual isolated photo journey|Present;synthetic/virtual latency evidence,not universal live SLA|
|10 Escalation/poll|active_risk.py;polling.py;scheduler auth/scripts;cross-store tests|Local path present;hosted Scheduler/OIDC acceptance deferred|
|11 Inventory|inventory.py;lift_first.py;test_inventory;actual Pro/immutable confirmation proof|Present;estimates anddisplayed subset remain explicit|
|12 Recovery|recovery.py;report_store.py;loss agent;test_reports;actual Pro/captured replay|Present;waterline retained as evidence;depth map is S5Stretch|
|13 Report|report-view.tsx;protected API/fragment auth;actual four-page native PDF|Present;full hashes/bytes/privacy verified|
|14 Packaging|api/web Dockerfiles;infra/deploy.sh;packaging tests|Final20–22 image refresh was missing;root now rebuilding/smoking exact source|
|15 Dashboard|dashboard-view/map;operator controls;strict DTOs;actual responsive/keyboard/runtime proof|Present;root verifying controlled tile-error state|
|16 Seed/reset|demo_seed/scenario;outcome seed;actual6-shop/reset/owner-binding proofs|Local approved substitute satisfied;second phone/redeploy deferred|
|17 Hardening|query lifecycle;protected recovery jobs;bounded retries;full gate;README architecture/setup/Built with|README screenshot deliverable absent;add sanitized current capture|
|18 Card|offline_card/card_renderer/service;RAQM/fonts;actual Telegram downloaded image|Present;airplane-mode test/human translation review not established|
|19 Policy|policy service/store/media/parser/agent;real synthetic default-delete/Keep/copy/delete proof|Present;provider backups/external copies not covered by local deletion claim|
|20 Waste|waste model/store/service;report;public summary;actual model/replay/PDF proofs|Audit found map layer missing; correction now source-reviewed, runtime verification pending|
|21 Public check|reader/intent/service/agent;actual source/Flash/handler proofs|Present;no fresh coverage or real second-recipient claim|
|22 Learning|outcome stores/service/history/analytics/seed;actual route/store/BQ proofs|Present;response coverage replacesaccuracy perapproval;protected job manual|

## Confirmed local corrections

1. **Safety priority: unavailable destination registry blocks fixed Danger fallback.** At the audited checkpoint, `DestinationLookup.nearest` propagated its bounded stream failure. Both `AlertComposer.action_snapshot` and `ReplyGuard.danger_reply` await it before rendering. Existing None-result test does not exercise an exception. Minimal correction: validate caller arguments as before; catch only source/transport failures around registry materialization, log a bounded class-only status and returnNone, so every existing caller uses its committed no-destination variant. No invented route or added Danger prose. Observe real composer and shared final-guard RED→GREEN with a raising SDK boundary; preserve invalid-argument rejection.
2. **Task20 waste map layer.** SourceR2/Task20 explicitly requires it; owner-confirmed labels/no invented geometry did not waive it. Approved minimal contract: public API adds bounded current-generation links from already-public synthetic shop IDs to their owner-confirmed street aggregate; no private coordinates/recipients/evidence. Frontend joins only current matching-generation dashboard shops. A cleanup layer identifies contributing synthetic shop locations and labels street totals as street aggregates, not per-pin totals or street boundaries/routes. Unknown/unassigned location remains table-only. Preserve keyboard/popup focus and all existing alert layers.
3. **Task17 README screenshots.** Add a sanitized current synthetic dashboard capture with accessible caption and source/version context. Final recorded-video/deck imagery remains separate; never include report capabilities or private recipients.
4. **Warning optional-update button.** Source6.2 asks for a button; the audited composer provided `/refresh` prose but only stock/vehicle/route buttons. No approved waiver found. Minimal follow-up is a bounded callback into the existing refresh flow with current owner/risk checks; no new video feature. Root authorized the owner-only callback contract described below.

## Section13 invariants

- Fixed Danger, earlier vehicle target,localized999: canonical rendering/tests exist; destination-only outage above must be corrected before reconfirming completeness.
- No unsupported advice/places: typed policy guards, fixed food rule and historical opening labels present;Stretch scam/electrical flows not implemented or claimed.
- Privacy: public synthetic allowlists,hashed recipients,private report capability in fragment andAuthorization,policy deletion exception,exact-generation media controls are implemented;cloud IAM/provider retention remains deferred.
- Honest UI: estimates/confidence/unknown coverage andunreviewed translation labels are implemented;calibration is response coverage,notaccuracy. Model/fixture/virtual/real boundaries remain explicit.
- Evidence: immutable originals/append-only receipts,with explicit policy exception;actual hashes/PDF andretention tests exist. No scene/time/location authenticity claim.
- Latency: actual synthetic photo journey6.366swhole/5.673sprocessing supports one localunder10s path;not a universal network/model or live-neighbour guarantee. Bounds/fallbacks mustremain.
- NoCI: no workflow/Dependabot/repository trigger added;root verified Actionsdisabled andsource scan. Tests/builds remainlocal.
- Code/config/tests: modules/typed boundary review,configurablemodels,secrets scan and25infra/629API/33web evidence present. FinalDocker parity is being refreshed againstlatestcode.

## Explicit deferred or non-implementation gates

Cloud provisioning/hosting/IAM/Scheduler,actual two-phone journey,native-language review,real-shop valuation validation,fresh official flood observations,phone airplane mode,final under3minute recording/deck/public-deployment/submission are not silently counted as done. Water-depth/flood-memory map,drain/reopening/scam/open-shop/voice/live-location remainStretch. A timed2:45 runbook and isolated coherent artifacts are not a completed continuous live video.

Root authorized all four concrete corrections after this audit. Application edits begin only from the scoped briefs above; no new stack/dependency/model/deployment is implied. Independent reviewers will recheck the resulting deltas and root will rerun relevant local/runtime verification.

## Corrected-source checkpoint (before final operational gate)

Astra personally implemented the bounded fixes; no new dependency or model call was needed. Both original independent Matt axes reviewed the actual delta against 4a992a4, including the three new test files, and returned **0 outstanding findings**. Their source review does not replace runtime acceptance.

- Registry transport failures now return no destination after caller validation, so both alert composition and the shared final guard render the exact committed Danger fallback. Four actual raised-boundary tests were observed failing before the fix; the focused safety/dispatch suite then passed33 cases. Error logging contains only the exception class.
- Waste responses carry a nullable scenario generation and at most50 public synthetic shop/street links. The store checks the generation again after reading; a racing reset yields unavailable quantities. The browser joins only matching-generation existing public shops. The optional cleanup layer keeps flood levels visible and labels popup estimates as shared whole-street totals; the table remains the sole summation. Unknown quantities remain unknown; no street geometry is inferred. Two backend and one frontend cases were observed RED before implementation; reset-during-read coverage was added.
- Warning includes the existing eight-language `video_update_optional` text as its optional update button. The callback prompts only a current owner, rejects a changed shop/role, and rebuilds the prompt after the inbox enters sending so arriving Danger replaces it. Failures before transport remain retryable; uncertain transport remains uncertain. Seven callback/composer cases were observed RED, then GREEN. Danger catalogs were not edited.
- Combined focused verification:58 backend cases,7 waste frontend cases, scoped frontend lint and diff whitespace check passed. New API cases total16 (6 Danger,3 map,7 Warning); new frontend case1. Expected consolidated totals at this historical checkpoint were645 API/34 frontend/25 infrastructure; the observed gate is recorded below.
- Root controlled basemap failure on the unchanged accepted build using a local CSP fault proxy:15 failed/0loaded tiles, visible synthetic pins, keyboard Retry retained explicit unavailable while the fault persisted, and Space still opened a shop popup. A normal reload outside the fault loaded15 tiles. This proves failure and retry-under-persistent-fault, not same-page reconnect recovery or phone airplane mode. Evidence: `task20-22-acceptance/ui/tile-failure-proof.json`.

README screenshots and final corrected-source container/browser/full-gate results will be recorded after root's capture and verification. The previous local acceptance has therefore been audited and corrected, not treated as a blanket completeness assertion.

The first corrected-source full gate was **not accepted**:25 infrastructure passed; API642 passed/3 failed in99.26s. Two existing real-Firestore vehicle tests still expected three buttons; they now require the approved fourth optional-update button's exact localized text/callback while preserving all existing vehicle/route and Danger assertions. Both reviewers returned0 on this test-only supplement. The third failure was exhausted Firestore transaction retries in a concurrent official-recovery test; root is reproducing it in isolation. Read-only inspection found both event application and recovery read risk, shop and current vehicle pointer in the same order. No retry-budget or product change was made on speculation. Log: `task20-22-acceptance/full-gate-audit-v1.log`.

Root then reran the unchanged risk case: all six parameter cases passed11.47s; three independent concurrent two-case batches passed8.77/6.91/8.68s. The original lock timeout remains observed and its cause unproven; no application fix is claimed. The next complete gate is serialized without a concurrent Docker build. Root's actual Firestore cleanup-map probe also passed using a controlled generation2 copy of the retained six-item synthetic report: one public link, estimated0.8m³/230kg, exact original fact hash unchanged. This establishes the new projection boundary, not a new model assessment or mutation of global data. Evidence: `task20-22-acceptance/ui/waste-map-actual-proof.json`.


## Final consolidated gate

Root confirmed `infra/test.sh` exited0 on the frozen reviewed correction: **25 infrastructure tests (6.140s),645 API tests/no skips/six dependency warnings (80.73s),34 frontend tests/no skips**, lint, typecheck and production build all passed. Log: `task20-22-acceptance/full-gate-audit-v2.log`. Counts reconcile as629 prior API +6 destination-outage +3 cleanup-map +7 optional-update cases; frontend33+1 map contract; infrastructure unchanged25. The two assertion corrections add no cases. Both independent review axes and the assertion supplement remain0 outstanding findings. Corrected-source browser/screenshots and final packaging are separately recorded below when observed.

## Post-gate runtime loss and explicit reconstruction

After the passing gate, root observed the ephemeral Firestore container exit with `OOMKilled=true` at2026-10-13T06:50:56Z during the web image-build window. Existing bounds were already a384MiB Java heap and768MiB container cap; no heap change is claimed as a fix. Root restarted only that same validated container through the lifecycle runner. GCS/PubSub remained running; subsequent inspection also found the BigQuery OOM described below. Prior owner registrations, ADK sessions and private report fixtures must be treated as lost unless explicitly reconstructed and verified; historical test/artifact evidence remains valid but is not proof of retained runtime state. Screenshots from lost fixtures are not described as current restored-state captures.

Existing no-send restoration entrypoints are `python -m api.demo_seed` (six virtual shops, inventories and destinations) and `python infra/seed_outcomes.py --apply` (labelled synthetic history). Reconstruction must avoid reusing old immutable outcome/media identities with new timestamps against retained analytics; use an isolated fresh dataset/generation or verified exact prior facts. Do not recreate private owner bindings or accepted actions from memory. Captured model-output replay in a new isolated namespace must remain labelled replay, not a new model call.

The official [gcloud Firestore emulator reference](https://docs.cloud.google.com/sdk/gcloud/reference/emulators/firestore/start) documents export-on-exit to a directory and import from an overall-export-metadata file. This is a possible future explicit checkpoint workflow requiring pinned-image validation; it has not been implemented here and cannot establish crash/OOM durability. The current correction does not add speculative memory settings or weaken tests.

Root also observed BigQuery OOMKilled at06:51:32Z, then restarted the same retained persistent volume; this is not a data replacement. Both current-source image builds nevertheless exited0. API container smoke passed health200,uid10001,required shaping capabilities and no.env; web passed root200/HighGround,invalid-report route200,protected proxy503 with intentionally absent backend,uid1000 and no.env. Both smoke containers were stopped. These are container compatibility/liveness checks, separate from service integration. Root is reconstructing six virtual shops and labelled history, then replaying captured synthetic model output into a fresh report namespace. Prior evidence/manifests are retained; owner/ADK history is not claimed restored. No application source or emulator configuration changed for this operational recovery.

Reconstruction evidence subsequently passed: retained analytics contained six old generation3 outcomes and six distinct new generation2 outcomes, with no duplicate identities; the rebuilt generation does not reuse the retained generation. A fresh captured-output recovery replay exited0 in2.413s with six items, three original hashes verified, private capability/worker rejection and duplicate idempotency. It reported an estimated RM850 loss from that captured synthetic assessment, not a new model call or real valuation. The owner street callback and a new controlled generation2 map projection passed (estimated0.8m³/230kg; source fact unchanged). Artifacts live under `task20-22-acceptance/post-oom-recovery/`; original pre-loss manifests remain intact. Root's current preview uses these newly reconstructed isolated facts. Final public-route/browser checks remain separate.

### Final phone-popup correction and runtime recheck

Root's recovered390px cleanup-map screenshot exposed zoom controls overlapping popup text. The screenshot is the observed RED (`post-oom-recovery/ui/cleanup-phone-map.png`). Astra moved Leaflet's existing zoom control into a labelled toolbar outside the map viewport, preserving library handlers and44px controls; only `dashboard-map.tsx` and scoped dashboard CSS changed. No report/print styling or backend code changed. Both original review axes are checking this supplement; root owns its final local entrypoint, actual close/zoom/popup verification and bounded web-image rebuild. Do not treat the earlier passing gate as verification of this later layout change.

Before that layout rebuild, the recovered actual API passed eight sequential/concurrent reads in0.739–2.468s with six current outcome responses; root retained `post-oom-recovery/runtime.log`. Root saved100 current Firestore documents including nested collections to a private0600 trusted local checkpoint. The dedicated local Buildx worker `highground-bounded` is capped at768MiB memory,1536MiB swap and1CPU, without auto-restart or a GitHub Actions context. This does not change the default builder, Docker VM or application container settings, and is not a promise of automatic Firestore persistence. API image parity independently matched all112 packaged source files.

The first full gate after the phone fix also exited0 (25/645/34 plus lint/type/build), but the final normal-flow status CSS was saved while it ran. Root therefore started another complete entrypoint against the frozen final two-file state; the earlier pass is not used to erase this timing ambiguity. No additional application scope was opened. Both original supplemental source reviews returned0. Standards freshly verified CSS SHA256 `5e166a8dbb4f687100565090b0e1bbdd8947d2a6387e99b8da84c786e6d32d19`; its earlier cached observation about absolute tile notices was corrected after a fresh absolute-path read.

## Final audit correction acceptance

Root's final frozen-source `infra/test.sh` v4 exited0: **25 infrastructure tests (6.563s);645 API tests (70.58s)/no skips/six dependency warnings;34 frontend tests/no skips;lint,typecheck and production build passed**. Both original independent Matt supplement reviews returned0 on the final two-file phone correction. This supersedes the timing-ambiguous prior run, not its retained log.

Actual 390×844 browser verification showed document scrollWidth 390 and an unobscured popup fully inside the map (left22/right369/top452;map starts447). Native keyboard zoom changed actual tiles from z13 to z14; zoom-out remained callable. Desktop 1512px also had no horizontal page overflow. Astra independently inspected both sanitized final images, then copied them byte-for-byte into `docs/images/cleanup-phone-final.png` and `cleanup-desktop-final.png`, with explicit controlled reconstructed-case captions in README. The four source-audit correction deliverables are complete. These images do not claim recovered private owner history or a fresh model inference.

The final bounded web-image rebuild is a separately tracked packaging check; root will append its actual result. Previously verified API image source parity is112/112 files with health/nonroot/shaping/privacy smoke passed. No application source edit followed the v4 freeze. External gates listed above remain deferred.

Root also repeated the tile-failure check on the final390px build: the normal-flow notice stayed below the map, three markers remained, four tiles failed under a controlled local CSP fault, and keyboard Retry retained explicit unavailability while that fault persisted. Screenshot: `post-oom-recovery/ui/tile-failure-final.png`. This still does not establish reconnect-and-Retry on the same page or phone airplane mode.

The first bounded final web-image build failed with ResourceExhausted/exit102 at768MiB, without emulator loss. Root is retrying with a1536MiB/2048MiB-swap build worker while deliberately pausing only HighGround Firestore and persistent BigQuery. The private100-document checkpoint is intended for verified Firestore restoration; no successful restore or packaging claim is made before its result. Other projects and the Docker VM are unchanged.

### Packaging and checkpoint restoration complete

The final bounded web-image retry exited0 with1536MiB memory/2048MiB swap; root stopped the builder afterward. Final container smoke verified uid1000, no.env, root200 containing HighGround, invalid-report route200 and protected API proxy503 with no backend deliberately attached. The smoke container was stopped. This completes final-source web packaging; API image parity remains112/112 files with prior successful nonroot/health/shaping smoke.

Root restarted HighGround Firestore and the retained BigQuery volume, then restored all100 checkpoint documents and verified exact equality with their saved original values (`post-oom-recovery/checkpoint-restore-proof.json`). This is a verified manual restore of the newly reconstructed state, not recovery of owner/ADK history lost before that checkpoint and not automatic crash durability. Main API8000/web3001 run again;8005/3003 serve the separately labelled reconstructed composite preview. Other projects and Docker VM configuration were unchanged. The four audit corrections, final local gate, both independent reviews, browser evidence, README screenshots and final packaging are complete; external gates remain explicitly deferred.

The final post-restore live read also passed: `/api/dashboard` available at generation2, `/api/outcomes` available at generation2, and `/api/waste` empty at generation2 (`post-oom-recovery/final-runtime.json`). Empty global waste is distinct from the separately labelled isolated cleanup-map preview; no preview assessment is attributed to the public six-shop runtime.
