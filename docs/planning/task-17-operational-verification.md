# Reviewed local operational checkpoint — 13 October 2026

Application code remained pinned to `f6efd31561c37bf3a59eb062215b244c7449b675`. Root performed the operations below after the corrected full gate (24 infrastructure,339 API,19 frontend tests, no skips; lint/type/build exit0) and independent Standards0/Spec0 rechecks. These are observed local results, not hosted acceptance.

## Shared factory and synthetic scenario

The actual API factory on loopback port8000 and the explicit seed command created six synthetic shops with three vehicles and default virtual recipients. Unauthenticated manual recovery returned403; the authenticated `/jobs/resume-pending` invocation returned200 with all three stages available and zero pending work. No automatic recovery schedule was created.

The production dashboard on port3001 exercised actual protected routes through a temporary authentication-preserving fault proxy. A Warning completed six virtual deliveries in the backend while the proxy deliberately lost its response. The proxy returned503 and the dashboard showed an unconfirmed operation; the web proxy sanitized the upstream error to502. An external authenticated reset advanced generation2. Retrying that exact UI intent correctly accepted the superseded response; a new click created a fresh Warning with six virtual alerts, zero real API acceptances and one current event. A Danger followed by the UI reset advanced generation3 and cleared current event/virtual counters. Historical facts were retained. This establishes the real superseded-response/retry integration, not an actual infrastructure outage.

Root subsequently inspected the direct primary dashboard DOM: RM472 estimated stock value reported lifted, one vehicle, one real acceptance,6.71-second displayed acceptance latency and five virtual alerts; the browser console had zero warnings/errors. The summary screenshot is retained privately as task17-dashboard-summary.png.

The temporary fault proxy was subsequently removed from the primary dashboard route: port3001 points directly to the reviewed API8000. A separate retained-report preview on3002 uses an isolated test adapter; it is not the ordinary application entrypoint. Evidence: private `task17-global-ui-result.json` and dashboard screenshot retained outside the repository.

## Consenting Telegram owner and immutable confirmations

Root restored the consenting own-chat registration through the actual Telegram interface and explicitly bound fixture1. Actual `PhotoStore` and `ReportStore` lookup continued to resolve the ordinary owner registration after binding.

One synthetic Warning was visibly received at07:05 Kuala Lumpur time with three displayed synthetic stock items totalingRM472. The vehicle target07:19 preceded the stock target07:34; these are action targets, not predicted flood arrival. The other five fixture recipients remained virtual. One initial UI request reached its ten-second deadline while the backend completed; retrying the identical intent confirmed completion without an extra real alert.

The owner clicked the actual vehicle and stock buttons. Two durable confirmation facts reached BigQuery. The dashboard showed one real Telegram API acceptance (recorded acceptance latency6709ms), five virtual alerts, one vehicle reported moved and RM472 estimated stock value reported lifted. These remain self-reported actions over synthetic inventory estimates; API acceptance does not establish reading or physical protection.

Root clicked both buttons again, then the final assertion exited0: still two facts, one reported vehicle, RM472 and one real accepted alert. The result is recorded in private `task17-own-chat-result.json`; no recipient identifiers, operator tokens or report capabilities are included in this document.

## Remaining gates

Actual operating-system Save-as-PDF/print output and pagination remain unverified because the desktop is locked. The complete local Must acceptance gate therefore remains open, and no Should implementation has started. Real Telegram media upload still awaits permission; actual second-phone and hosted acceptance are deferred. Previously recorded configured-model and original-media emulator journeys remain separate evidence. No deployment, CI, guessed recipient or claim of genuine/safe media or routes was introduced.

## Native-print follow-up: emulator recovery

The subsequent print-correction full gate reached334 API passes and five failures: four materialized BigQuery queries whose exact-result cleanup failed, and one concurrent Firestore claim lock timeout. Both services initially remained running without OOM/restarts. An isolated SELECT7 reproduced the cleanup timeout (query9.509s, delete10.006s, total37.653s). A BQ-only restart against the same retained catalog then failed with OOM at768MiB. Temporarily raising only that container to1536MiB allowed a slow start but did not restore bounded query performance; the higher limit was not the fix. No Docker VM memory increase or unrelated-container restart was performed.

Root retained the clean8,306,688-byte stopped database backup and used a reviewed copy-only recovery script. It removed exactly138 existing query-result datasets proven by job/project/dataset/table identity. Four business datasets,16 business tables, all875 job rows and retained metadata/schema were verified unchanged; the original backup remained unchanged. Of the derived results,114 were dashboard-stats queries, six stock aggregates and18 other SELECTs. This identifies the main producer, not whether an old frozen runtime or a failed current cleanup left each result.

Three isolated probes using the same image/config and original768MiB limit returned correct rows with cleanup success in4.505/6.509/5.324s. Root restored that verified copy to the stopped owned volume, restored768MiB memory/1024MiB swap bounds and started it through the reviewed runner. No application/backend/config change was made for this recovery. The full gate is being rerun; startup/probe success alone is not full acceptance.

Separately, an unchanged Firestore serial claim control passed in0.185s and five fresh-namespace concurrent controls returned exactly one claimed and one busy each (2.06–4.49s). The earlier lock timeout was not reproduced, so no claim-logic fix or test relaxation was made. Actual PDF content has since passed after the two-file frontend correction; final full-gate and independent review evidence remain separate.


## Final local Must acceptance

At print correction5be7f18, actual native PDF verification passed: two A4 pages, all three full hashes exactly once and byte counts, simulation/estimates/disclaimers retained, capability absent from text/links, readable complete pagination. Both independent Matt axes returned0 findings. The recovered-runtime full gate exited0:24 infrastructure (16.346s),339 API (no skips,five dependency warnings,163.75s),19 frontend tests with no skips, lint/type/build. Three actual factory dashboard reads returned200/available metrics/six synthetic shops in3.544/5.436/4.190s; dataset count remained4 before/after with no additions/removals. This closes the full local Must gate and permits dependent Should work. Hosting, second-phone and actual Telegram media-upload acceptance remain separately deferred; no cloud provisioning or deployment is inferred.
