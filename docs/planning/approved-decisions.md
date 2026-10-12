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
