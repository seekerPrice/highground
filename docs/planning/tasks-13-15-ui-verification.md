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

## Remaining acceptance

An actual printed PDF, its pagination/content and the OS print dialog remain unverified because the desktop is locked. Root already requested unlock; the browser API offers no print-to-PDF operation, and no alternative browser automation or security workaround was used. Save as PDF being keyboard-reachable does not establish successful printing. Current six-shop scenario/reset, live counters, complete local Must integration and final independent code reviews remain separate gates. Hosting, second-phone acceptance and actual synthetic-file upload to Telegram are still deferred.
