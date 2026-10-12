# Task17 protected manual outbox recovery

This backend slice follows the frozen, source-reviewed Task16 export. It adds no cloud schedule, deployment or new dependency. Root owns final gates, runtime and publication; the separate infrastructure lane owns local initialization/test hygiene.

## Entrypoint and bounds

`POST /jobs/resume-pending` uses the same exact Scheduler authorization as warning polling. Local operator authentication requires `SCHEDULER_LOCAL_AUTH=true`, `LOCAL_DEVELOPMENT=true`, `DEMO_MODE=true`, a private operator token, a validated loopback Firestore endpoint and no hosted `K_SERVICE`. The actual local recovery factory additionally validates explicit loopback Pub/Sub and BigQuery endpoints before constructing a client, preventing a missing emulator setting from falling back to cloud sinks. Hosted authorization uses the configured OIDC audience, exact verified service-account email and numeric subject.

The optional body is `{ "limit": 10 }`, an integer from1 through20; unknown fields, booleans, malformed/excessive bodies are rejected. The default is ten entries **per stage**, at most thirty admissions; the maximum is sixty. The response contains only counts/status for `dispatch`, `confirmations`, and `media_ledger`, plus a fixed uncertainty note; no event/media/confirmation identity, recipient, snapshot, SDK body or capability leaves this boundary. Successful responses have `Cache-Control: no-store`.

Stages run independently with a thirty-second response deadline (service test injection is bounded to at most45 seconds). Each scan has an explicit five-second SDK timeout and no transport retry; downstream work retains its existing bounded model/transport calls, leases, immutable identities and progress. One stage’s outage does not prevent another stage from progressing. Work still running when the deadline expires is retained by the owning service, reported `deadline_limited`/`inflight_unknown`, and blocks duplicate stage admission on that service until it actually finishes. A response timeout does not cancel or prove cessation of a thread’s external request. Shutdown waits for retained work before closing its owned clients, and independent client closure proceeds even if another close fails.

Dispatch replay uses the existing final Danger, episode and scenario-generation guards. An obsolete generation is suppressed without model/transport/sink work. Previously accepted or uncertain sends are not blindly sent again. Vehicle and stock confirmations share one pending-confirmation scan/flush path. Ledger recovery selects only `storage_status=done, ledger_status=pending`; it does not create a downloader, invent a Telegram file identity, request a new upload or ingest an upload whose original is missing. Stored receipt facts and logical identities remain unchanged.

## Manual invocation

Configure the ignored private `.env` and explicit loopback services, then invoke the running local API without printing the token:

```sh
.venv/bin/python - <<'PY'
import os
import httpx
from api.config import load_settings
from api.tools.emulators import loopback_endpoint
settings=load_settings()
origin=loopback_endpoint(os.environ.get('API_BASE_URL','http://127.0.0.1:8000'),http=True)
response=httpx.post(origin+'/jobs/resume-pending',headers={'Authorization':'Bearer '+settings.operator_token},json={'limit':10},timeout=45)
response.raise_for_status()
print(response.json())
PY
```

This is authenticated **manual** recovery. No running automatic schedule was created. After hosting is explicitly authorized, a resumer schedule can call this exact route with the same configured OIDC audience/caller identity and a bounded body; its actual recurring invocation must be tested before calling recovery automatic. Existing warning polling is a separate job.

## Dashboard query lifecycle

Dashboard analytics now uses the reviewed `api/tools/bigquery_queries.py` helper while preserving all parameterized current-ID allowlists, distinct/MAX aggregation, query/result timeouts, billing bound and unavailable-state validation. Only an explicitly configured matching loopback client may delete its exact current result destination (`project` match and `dataset_id == table_id == job_id`). Production/unset/empty optional emulator configuration never triggers cleanup.

Already materialized valid rows remain usable even if local cleanup fails. Sanitized log messages and `DashboardAnalytics.last_cleanup_status` expose cleanup outcome; private SQL, row values and SDK response bodies are excluded. Original query failures still yield unavailable stats; the helper retains the original exception and only attaches sanitized cleanup notes. No job listing, prefix sweep, shared scratch table or direct database mutation is used.

## Evidence

- Initial public route guard RED: missing authorization expected403, actual404 (`1 failed`, exit1, 0.80s); wired endpoint GREEN.
- Actual Firestore/protected HTTP journey: accepted Warning with failed optional sinks, private vehicle+stock callbacks with failed analytics, and a stored original with pending ledger. After sink recovery, authenticated HTTP invocation completed one event, two distinct immutable confirmation facts and one logical receipt. Duplicate webhook/job replays added no send, acknowledgment, confirmation or download; missing-storage upload remained pending. Transport/storage/analytics are explicit doubles in this regression, with actual Firestore transactions and actual public handlers.
- The full public outage/recovery assertion was watched RED in an isolated source copy with per-item worker execution deliberately replaced by an unwired no-op: completed0 versus required1 (`1 failed`, exit1, 0.72s). Current real workers passed. Shared source/runtime was never reverted; temporary copy removed.
- Deadline, independent-stage failure, repeated invocation, owned client closure, exact auth/local hosted/cloud refusal, malformed bounds and obsolete-generation suppression have focused tests.
- Empty optional BigQuery host seam RED: unset succeeded but empty yielded unavailable (`1 failed,1 passed`, exit1, 0.49s). Normalization to disabled/None made both cases GREEN.
- Actual official BigQuery dashboard/helper probe: duplicate virtual input rows aggregate to one virtual alert, zero real API acceptances, null real acceptance latency; an absent expected virtual analytics identity yields unavailable, not zero. Both exact query results were cleaned. Probe work5.373s; process exit0; exact owned dataset deleted with timeout25 and client closed. No GCS/Pub/Sub/model/Telegram call or shared data mutation.
- Final focused gate: **29 passed, no skips, 3.79s, exit0** across recovery jobs, Scheduler auth, dashboard and query-helper tests with isolated Firestore/BigQuery services.

Astra independently inspected the final resumer, protected route and dashboard/helper integration, then ran the actual-Firestore protected-route/dashboard tests: **13 passed, no skips, 1.92s, exit0**. No additional concrete defect remained in that focused review.

Final consolidated gate, actual factory/local protected route journey, browser/PDF gates and both Matt axes remain parent-owned acceptance work. No automatic scheduling or deployed acceptance is claimed.


## Historical outbox correction at8be5884

The Spec review identified that reset suppression returned before optional event/alert sinks and removed the event from pending scans. Obsolete-generation delivery now remains suppressed while sink-only recovery preserves historical progress. Its public response remains `superseded` with the known reason; its private status remains `pending` until history actually completes, and protected recovery counts that truthfully. No model, risk/action preparation or Telegram send occurs on this path. Existing accepted/uncertain/simulated factual statuses remain; unsent children become superseded with non-accepted analytics, prior sending children become uncertain.

A bounded exact-event child lookup (maximum1000, fail closed above that scope) includes alerts persisted before parent alert IDs/prepared progress committed. Both affected final suppression branches retain pending analytics rather than claiming a write occurred. The common existing sink boundary flushes each stable logical identity and then makes the obsolete event terminal; current-generation dashboard allowlists exclude that history.

Observed actual Firestore/public HTTP RED: accepted send plus optional sink outage, then reset, falsely reported no pending dispatch (`1 failed`, exit1, 1.76s). Corrected source resumes one logical event/alert history without another old send; repeat is empty and fresh-generation metrics remain scoped. A temporary isolated copy restored only dispatch/store/recovery job files from baseline8be5884: pending/sending/simulated orphan-child regressions all failed (`3 failed`, exit1, 0.76s). Current source passes all three; copy removed, shared source/runtime never reverted. Final affected gate before the legacy-shape assertion:121passed,2explicit integration skips,13.01s,exit0. Skips were inventory real-GCS integration and stock real-analytics integration, because this correction run intentionally configured Firestore only; root owns the consolidated all-service gate.

Final focused correction gate: **37 passed, no skips, 3.13s, exit0**. Astra independently inspected the changed lookup/history paths and ran **9 targeted cases passed, 28 deselected, 1.54s, exit0**. API collection increases from332 to339: three binding/guard/callback cases, three persisted-child states and one reset variant of the existing outage journey. Root will run the complete all-service gate before both independent reviewers recheck the pinned correction.
