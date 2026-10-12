# Approved decisions

User approval recorded 13 October 2026. These amendments supersede conflicting wording in the preserved handover and older planning drafts. The latest authorization below supersedes earlier individual Task N gates.

## Delivery order and earlier progress

- Q1 accepted: Task 15 follows Task 14, with the Must dashboard included in the Thursday deployment target. Task numbering remains for traceability; individual Task N gates are superseded by the latest authorization.
- The user clarified that dates must not prevent earlier progress. Day allocations are targets, not earliest-start restrictions. A later task can start earlier once its prerequisites pass.
- Earlier rule (superseded for local coding by the local-first section below): Should tasks remained behind deployed acceptance of Tasks 1–17; there is no requirement to wait until Friday. Stretch stays pitch-only. Code-freeze and submission deadlines are not extended.
- Latest user authorization: implement all tasks, parallelize where possible, and do not wait for calendar allocations. All implementation is authorized subject to actual prerequisites; The later local-first amendment defines the current Should gate. Stretch stays pitch-only.

## Official data and simulation

- Q2 accepted: reject stale readings for current alerts; show stale/unavailable source status; use explicitly labelled simulations in the demo when necessary.
- A working polling endpoint plus simulations does not establish working live official flood warnings. A fresh official source remains unresolved.
- Timestamp freshness thresholds and geographic/type mapping are decisions for the data-client task; this approval does not invent their values or authorize a replacement provider.

## Alert safety contract

- Q3 accepted: use two deterministic action targets with vehicle strictly before stock. Never present them as predicted flood-arrival times.
- Danger output remains a fixed, committed template. Reconcile the emergency footer within that template and provide a fixed missing-destination fallback; no runtime translation or generated additions.
- Destination wording must not guarantee site or route safety. The exact fixed wording, translations, allowed placeholders and deadline configuration will be established in the relevant task before use.

## Engineering workflow

- For an ordinary decision presented with a recommendation, the user authorizes choosing it after five minutes without a reply and recording the decision. Individual Task N gates are superseded; missing facts and credentials cannot be assumed.
- Astra coordinates 6.1 Sol: brief, implementation, review of actual files and local results, correction requests to Sol, and recheck.
- Keep the internal checklist current. Matt's independent Standards and Spec reviews inspect each task's changes; meaningful findings are corrected and reviewed again.
- Strictly no CI: no GitHub Actions/workflows, Dependabot or repository-linked Cloud Build triggers. Tests, builds and deploys are invoked locally.

## Execution ownership and infrastructure boundary

- Astra owns task briefs, dependency/checklist updates, review and correction coordination. Disjoint implementation slices may run on two 6.1 Sol agents concurrently.
- Root handles external prerequisite discovery and GitHub/commit integration. Shared entrypoints and dependency locks have one assigned owner at a time.
- Local scripts and parsers can be implemented/tested while credentials are missing. Actual cloud provisioning requires an explicit HighGround target project; never use an unrelated active gcloud project implicitly. Report implemented, locally verified, provisioned and deployed as distinct states.

## Latest local-first authorization and concrete defaults

- The user requests fully local implementation first and hosting later. This supersedes the older deployed-before-Should coding gate: verify all Must behaviour locally before local Should implementation. Do not claim cloud provisioning, live hosted acceptance or deployment complete.
- Root may create a dedicated HighGround project and link the explicitly approved zi kang billing account. Resource provisioning and deployment remain deferred. Task 2 scripts can be implemented/tested locally; Task 14 packaging/local container checks can be prepared with deployment status pending.
- Q3 approved: public dashboard exposes synthetic demo records only; operator token protects simulation/reset; loss reports use unguessable bearer links and private media; use File integrity verified; confirmations count exactly their displayed inventory/action snapshot.
- Q4 approved: configurable station freshness exclusion of 90 minutes; reject missing/future timestamps and exclude marine/unmapped observations from local warning dispatch. This is not a claim about official source cadence.
- Q5 approved: vehicle action target 15 minutes and stock action target 30 minutes from warning creation; Danger bypasses property actions. These are action targets, not flood-arrival forecasts.

## Fixed Danger rendering contract

Routine implementation of the approved safety amendment: each language has four committed variants, destination/no destination crossed with real/simulated. Simulated variants begin with an inseparable fixed `SIMULATION` label in that language. Unreviewed translations include their fixed machine-translation review notice inside the committed template. Runtime never appends generated prose or notices.

English destination variant: “⚠️ DANGER: Flooding is reaching your area. Leave now and move to higher ground. Do not stop to record video or move stock. Listed destination: {safe_point_name} {route_link}. Availability and route conditions are unverified. Call 999 in an emergency.”

The no-destination variant replaces the two destination sentences with “No listed destination is available.” Only validated destination name and route link are substituted. There are no stock/vehicle actions or video requests, and only a route button when a destination exists. These templates do not assert a route or site is safe or open.

## Constrained Warning composition

The recommended amendment was presented at18:08:38 UTC and remained unanswered at18:13:51 UTC. Under the user's explicit five-minute default, adopt configured Gemini selection among approved localized message structures/situation sentences with a strict schema. Canonical actions, item/value snapshots, targets, destination labels and route links are rendered deterministically; bounded failures use fixed fallback text. Arbitrary model/operator reason text cannot re-enter recipient instructions through an unchecked placeholder.

This intentionally narrows the original free-form “Gemini-written message” requirement because unrestricted prose cannot be reliably screened for unsafe advice in all eight languages. Gemini remains genuinely invoked for constrained selection and for the separate photo/inventory/loss tasks. Danger remains an absolute model bypass using its committed variants. Detailed attributed triage reasons can remain in private event records and the appropriately filtered demo feed.

## Independent report corroboration

For Task 9, interpret the two-report rule as two distinct registered shops within 500 metres and 30 minutes, excluding duplicate media/report identities. This conservative implementation interpretation prevents two repeated uploads from one shop from manufacturing corroboration. A single photo's specified confidence/water-inside rules remain unchanged, and official Danger cannot be reduced by shop reports. The event point stays the current report's confirmed location; no centroid or source attribution is invented. Astra proposed this interpretation and the coordinating parent accepted it before implementation.

Section 6.1 independently permits two reports without model verification. Confirmed, non-rejected unverified reports therefore remain eligible when the model is unavailable, unreadable or uncertain. Explicit negative, unrelated, staged, screenshot and old assessments are excluded. Two such independent reports produce Warning, never Danger; the reason identifies unverified corroboration rather than implying visual verification. Preserve each assessment's status and confidence. This is source conformance confirmed during Task 9 review, not a new product scope.

Preserve each supported photo accepted from an authenticated registered shop immediately, before location confirmation: original bytes/hash and ledger receipt retain explicitly unconfirmed/default-shop location provenance. Confirmation appends separate immutable report-location facts used for triage, without rewriting the receipt. Unconfirmed photos create no neighbour event and do not enter the corroborating evidence window. The operational ten-minute submission throttle may reserve at initial accepted upload; it is distinct from confirmed evidence-window inclusion. Unsupported, unregistered or oversized uploads remain rejected. Duplicate delivery/restart reuses the same media identity. This implements S4's preservation requirement rather than narrowing it to completed reports.

## Active Danger and recovery prompts

The fixed-template safety rule also applies to follow-up actions: no request for another photo/video or property action while current Danger applies. This covers onboarding completion, baseline refresh, optional Warning updates and `/report` or after-flood prompts. User wording alone does not resolve an active official Danger, and stale/unavailable data does not clear it. Recheck immediately before prompting after asynchronous media processing; unsolicited evidence may be recorded without asking for further exposure.

Official Danger resolves only through fresh explicit official recovery for the same source/episode. Photo-only Danger may enter an explicitly owner-declared recovery workflow, with self-reported provenance, only when no active official Danger applies. `/report` alone is not that declaration, and the workflow never claims the area is safe. Recheck official escalation immediately before each media prompt. Demo Danger clears only through operator-controlled scenario reset. This distinction was confirmed by the coordinating parent before Task 10 integration.

## Confirmation aggregate semantics

Use an explicit shop/episode scope, distinct from event and recipient IDs. A vehicle counts once per shop/episode. For stock, take the highest value of an actually displayed and confirmed immutable snapshot per shop/episode, then sum across shops. Preserve every authorised action fact in the ledger; duplicate recipients, repeated Warning events and inventory refreshes cannot inflate this aggregate. Label it “Estimated stock value reported lifted” and make the definition accessible.

This is a conservative snapshot metric, not a union of unique physical items or proof of financial loss avoided. It includes no hidden items, inferred salvage or insurer-assessed value. Astra proposed and the coordinating parent confirmed this routine implementation of the approved no-double-counting policy. Tests span different event IDs, owner/worker taps, refreshes and episode boundaries; an explicit synthetic scenario reset does not resolve real official Danger.

## Current emergency contact for the future offline card

The Task 18 recommendation was presented at 18:50 UTC and remained unanswered at 18:56 UTC. Under the user's explicit five-minute default, use **999 only**, replacing the handover's separate Bomba 994 line. [MyGOV's MERS 999 page](https://www.malaysia.gov.my/en/categories/safety-and-community/public-safety/mers-999-emergency-line) includes the fire and rescue service; [Civil Defence's emergency-service explanation](https://www.civildefence.gov.my/999-emergency-services/?lang=en) states that 991/994/999 were merged into 999. Existing fixed Danger templates already use 999 and are unchanged. This decision does not authorize early Should implementation; the original source handover remains preserved.

## Local acceptance test recipients

The recommendation was presented at 19:15:40 UTC and remained unanswered at 19:21:16 UTC. Under the user's five-minute default, local Must acceptance may use six explicitly synthetic shops, the user's consenting HighGround chat and virtual recipients for controlled delivery tests. This permits the local Must gate to be completed before Should implementation without inventing a second tester. Actual two-phone and hosted acceptance remain separately pending and must be reported as such. Synthetic data and messages retain their labels; virtual delivery is never described as Telegram delivery to a real neighbour.
