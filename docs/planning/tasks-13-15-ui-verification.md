# Report/dashboard UI follow-up — 13 October 2026

Root built the frozen Task16 frontend candidate with `npm --prefix web run build` (exit 0), then ran the production Next.js server on loopback 3001 against an isolated preview API on 8001. The preview snapshots the current API source and uses the retained, actual-model recovery fixture through its real capability-authorized report router. It does not run the global bot, seed global shops, call models or query BigQuery. Dashboard analytics are explicitly unavailable in this preview.

## Observed browser results

The Chrome extension controlled the actual production pages. The report rendered three assessed baseline item groups, RM220 estimated loss and three receipts from the retained synthetic recovery probe. This amount is a model output on synthetic still-derived inputs, not a real-shop valuation accuracy claim. The earlier probe substituted the Telegram download/recipient edges; UI receipt rendering is not evidence of an actual Telegram upload.

- The selected after-video is labelled “After video used for assessment”; item timestamps explicitly refer to that video.
- Keyboard Tab from the brand link reached Save as PDF. Enter on Verify file integrity completed a real stored-file check and displayed File integrity verified.
- At a 390px viewport, both report and dashboard had a 390px document width, with no page-level horizontal overflow. The report comparison table intentionally scrolls within its 620px container. Full-page screenshots were inspected.
- Keyboard Enter on the dashboard's synthetic shop list selected that shop (`aria-pressed=true`), providing a map alternative. Leaflet/OpenStreetMap attribution remained visible.
- Dashboard source/analytics unavailability was explicit; unavailable counters were not rendered as zero. Virtual alert copy distinguished local simulation from Telegram acceptance or phone delivery.

## Isolated UI-state fixtures

A temporary out-of-repository adapter kept report authorization and original stored bytes intact while returning deliberately changed display states. These checks prove frontend rendering/retry behavior, not that real storage was corrupted or that a production outage occurred.

- Partial coverage displayed Partial estimated loss, one Unknown row and the exclusion of unknown losses.
- No assessed items displayed Unavailable and three Unknown rows, not a zero-loss estimate.
- Integrity mismatch displayed File integrity mismatch, no verified badge, and blocked original playback with an explicit failure message.
- Media unavailability displayed the unavailable verification message, no verified badge and a retryable original-loading message.
- Report service failure displayed The report could not be loaded; keyboard retry recovered the actual report after the adapter returned to normal.
- An empty dashboard displayed zero synthetic shops and No synthetic shops are available.
- Dashboard service failure displayed explicit unavailability; keyboard retry restored the map/content after the adapter returned to normal.

Both browser tabs returned no captured warning/error console entries at the end of these checks. Temporary viewport overrides were reset and the adapter returned to real-data mode. The snapshot, private fixture configuration, logs and screenshots are retained outside the public repository; no capability was printed or added to this document.

## Native print follow-up and remaining acceptance

After the user unlocked the desktop, the native system dialog saved a three-page A4 PDF. Its simulation, estimates and disclaimers were present and the private capability was absent, but verification against the authorized report response found all three full hashes and byte counts missing. Closed disclosure contents were not printed despite the existing CSS. This is a demonstrated Task13 defect, not evidence that the blocking `window.print()` call itself was faulty.

Sol supplied a minimal correction in the report component and print stylesheet: explicit print-only full receipt fields outside the disclosure, hiding screen disclosures during print regardless of their open state, with modest print spacing changes. Astra inspected the patch. Root then exported the corrected report through the actual Chrome/macOS native print dialog: two A4 pages,56,506 bytes. The private PDF verifier exited0: all three full hashes occur exactly once, all three byte counts are present, the capability is absent from text and links, and simulation/estimate/disclaimers remain. One screen disclosure was open and two were closed. Root and Astra inspected both rendered pages: readable complete receipts, clear table columns and no clipping. Three verified badges followed actual stored-file checks. Independent Standards and Spec reviews of13e1678…5be7f18 each returned0 findings.

The full local gate attempted after this correction reached334 API passes and five failures (251.02s, five dependency warnings): four exact BigQuery result-cleanup failures despite correct materialized rows, and one Firestore concurrent-claim transaction lock timeout. Neither emulator restarted or reported OOM. The serial Firestore claim control passed in0.185s; five unchanged fresh-namespace concurrent runs each returned exactly one claimed and one busy (2.06–4.49s). This does not reproduce or explain the earlier lock timeout. BQ query timing subsequently reproduced a10-second result-deletion timeout and the retained database failed a768MiB restart with OOM; root isolated catalog recovery on a preserved copy. Exactly138 metadata-proven derived result datasets were removed from that copy;16 business tables,875 job rows, retained metadata/schema and the untouched original backup were verified. Three isolated same-image768MiB probes passed with correct rows and cleanup (4.505/6.509/5.324s), then the verified copy was restored to the stopped owned volume and the original768MiB bounds restored. These checks justify recovery, not a claim that every historical cleanup failure is explained or that no future failure can occur. No backend fix, retry-limit change or relaxed assertion is inferred. Frontend stages did not run in that failed full gate. A separate explicit unit gate passed24 infrastructure,170 API with169 integration skips,19 frontend tests and lint/type/build; it is not full integration acceptance.

The six-shop scenario/reset, live counters and independent reviews of the earlier f6efd315 application have since passed; see `task-17-operational-verification.md`. The native PDF content check has passed; the recovered-runtime full gate subsequently passed24 infrastructure/339 API (no skips,five dependency warnings,163.75s)/19 frontend tests plus lint/type/build. Independent print reviews passed0/0. Three actual factory dashboard reads returned200 with available metrics/six shops and no dataset growth (4→4). The complete local Must gate is accepted. Hosting, second-phone acceptance and actual synthetic-file upload to Telegram remain separately deferred. No Should implementation has started.
