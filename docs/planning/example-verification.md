# Public worked-example verification

Issue [#31](https://github.com/seekerPrice/highground/issues/31); implementation baseline `6c71dc456453e3c20a56247e4daa56a0a79312a1`. Actual working delta was read with GitButler because its workspace commit is synthetic. This record separates source review from root-owned runtime acceptance.

## Implementation and Astra inspection

Sol implemented static `/example`, an unconditional dashboard navigation link, narrow typed calculation module, exact public PNG copies, scoped CSS and three fixture/provenance checks. Astra created the brief, curated public fixture and provenance record, then inspected actual code. Early findings were returned to Sol and rechecked: group counts now derive from rows; conditions/uncertainty are attributed to recorded model output; the no-visible-loss label makes no safety claim; action targets are explicitly illustrative configurable defaults; image dimensions/lazy loading and page metadata are present. No private report API or model call is used.

Observed Sol local checks: 37 web tests passed, lint passed, typecheck passed. The initial unsupported Next lint-rule directive was removed and the check rerun successfully; it does not remain in source. No build or runtime was started by Sol/Astra.

## Matt Standards

Independent read-only review returned **0 actionable findings**: no documented standards breaches or heuristic smells needing correction. Checked approved stack, small typed modules, synthetic/estimate labels, privacy and checksum limitations. Runtime/full acceptance was not inferred from this review.

## Matt Spec

Independent read-only review returned **0 actionable findings**: no missing/partial requirements, scope creep or incorrect implementation. Checked issue31, brief and authoritative amendments against captured facts, ranking logic, narrow projection, confidence/count caveats and checksum limits. Reviewer independently ran the three new example tests; all passed.

## Isolated negative guards

After implementation, Astra copied the nine relevant test/data/module/media inputs into a temporary directory. Three separate mutations proved that the new tests detect regressions: changed captured rice quantity produced two failed tests; injected `report_id` produced one failed allowlist test; appended bytes in the public PNG produced one failed file-equality test. Restoring the copied originals produced three passing tests. These are observed post-implementation mutation checks, not a claim of test-first development. Every original shared input retained its original SHA-256 throughout.

Logs and source hash manifest: `/Users/lucaslt/.codex/outputs/highground/example-review/guard-proof.json` and sibling logs. These local operator paths are evidence locations, not public links or credentials.

## Root acceptance

The first full entrypoint exited1:641 API cases passed and four BigQuery cases failed with ReadTimeout after339.60seconds; frontend stages were not reached. API source is unchanged. Root independently observed a three-second dataset-list request timing out, the existing emulator running with OOMKilled=false and high CPU, and repeated transaction-already-committed log errors. These establish unavailable emulator behavior, not a proven application defect or precise root cause. Root is recovering only the existing owned BigQuery container with its verified retained volume, then rerunning failed cases and the full gate. No API source fix is claimed.

Root separately observed production port3006 with deliberately absent backend: `/api/dashboard` returned503 while `/example` remained usable. Desktop1512px and phone390/320px had no horizontal page overflow; stage anchors, horizontal table ArrowRight movement (40px) and a3px focus indicator worked. These browser checks preceded the narrow Gemini label follow-up and do not replace the final build.

The two-copy Gemini follow-up was approved from recorded Vertex provenance, implemented by Sol, and rechecked by Astra. All37 web tests, lint and typecheck passed again. Both original independent Matt reviewers returned0 on the narrow supplement. Final root full gate/build/publication remain pending. Hosting and human/external submission gates remain pending.

Root reran the exact four previously failing BigQuery cases after restarting the same owned emulator with its retained volume: **4 passed in91.82seconds**, with no application source change. This demonstrates recovery for those cases, not a proven permanent cure. Read-only Astra diagnosis confirmed that the existing query lock is process-local, while the dashboard polls every3seconds and outcome panel every10seconds; independent processes and dataset setup/cleanup do not share that lock. The prior verification record already requires coordinated emulator-heavy probes. Root is running the final full gate with only the owned main API process temporarily suspended and an exit trap to resume it. The backend-independent example remains available separately. No query-history deletion, memory increase or application patch is claimed.

## Final local entrypoint

Root's final isolated `infra/test.sh` exited0: **25 infrastructure tests (7.051seconds),645 API tests (97.16seconds),37 web tests; lint, typecheck and production build passed**. API and web had no skips; API emitted six dependency warnings. The existing main API was temporarily suspended during the gate to remove competing browser polling, and the exit trap resumed it (process state Ss confirmed). The previous four failures and their91.82second recovery rerun remain recorded above; this passing run does not establish a precise timeout cause or automatic durability fix. No API/application logic or container configuration changed during recovery.

Root started the final production build on the main local3001 preview and separate3006 backend-unavailable preview. Final Gemini-copy browser/screenshot and resumed-runtime checks are imminent, so they remain distinct from the completed full gate. Publication and external hosting/human gates are still root-owned.

## Final browser and runtime recheck

The final build returned HTTP200 for `/example` on main port3001 and the deliberately backend-unconfigured port3006. Root reloaded the latter and observed the final Recorded Gemini output label, then inspected the main page. Both original PNGs loaded, final1512px/390px/320px document widths matched viewports, and the final phone caption displayed the Gemini label. Earlier same-layout checks established stage navigation, keyboard table scrolling/focus, checksum disclosure and dashboard-to-example navigation while `/api/dashboard` returned503. Final screenshots are `worked-example/final-desktop.png` and `final-phone.png` in the local outputs directory.

The resumed main API retained six synthetic shops but initially reported unavailable statistics. After a second restart of the same retained BigQuery container and an explicit ready check, outcomes and dashboard statistics returned available (8.186s and7.517s for those requests); an earlier dashboard request remained unavailable. This is observed local emulator recovery, not reliable latency or permanent stability evidence. No source, retry, memory, volume or private-data change was made. The new static example does not depend on this emulator. Docker images were not rebuilt for this frontend-only refinement; the production Next build and actual browser are the verified artifacts. Hosting, human validation and final submission remain deferred.
