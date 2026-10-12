# Approved decisions

User approval recorded 13 October 2026. These amendments supersede conflicting wording in the preserved handover and older planning drafts. They do not authorize tasks beyond the one the user names.

## Delivery order and earlier progress

- Q1 accepted: Task 15 follows Task 14, with the Must dashboard included in the Thursday deployment target. Numbering and individual Task N gates remain.
- The user clarified that dates must not prevent earlier progress. Day allocations are targets, not earliest-start restrictions. A later task can start earlier once its prerequisites pass and the user authorizes it.
- Should tasks remain behind deployed acceptance of Tasks 1–17; there is no requirement to wait until Friday. Stretch stays pitch-only. Code-freeze and submission deadlines are not extended.
- Task 1 is explicitly authorized. No authorization to start Task 2 is implied.

## Official data and simulation

- Q2 accepted: reject stale readings for current alerts; show stale/unavailable source status; use explicitly labelled simulations in the demo when necessary.
- A working polling endpoint plus simulations does not establish working live official flood warnings. A fresh official source remains unresolved.
- Timestamp freshness thresholds and geographic/type mapping are decisions for the data-client task; this approval does not invent their values or authorize a replacement provider.

## Alert safety contract

- Q3 accepted: use two deterministic action targets with vehicle strictly before stock. Never present them as predicted flood-arrival times.
- Danger output remains a fixed, committed template. Reconcile the emergency footer within that template and provide a fixed missing-destination fallback; no runtime translation or generated additions.
- Destination wording must not guarantee site or route safety. The exact fixed wording, translations, allowed placeholders and deadline configuration will be established in the relevant task before use.

## Engineering workflow

- For an ordinary decision presented with a recommendation, the user authorizes choosing it after five minutes without a reply and recording the decision. Explicit Task N authorization gates remain; missing facts and credentials cannot be assumed.
- Astra coordinates 6.1 Sol: brief, implementation, review of actual files and local results, correction requests to Sol, and recheck.
- Keep the internal checklist current. Matt's independent Standards and Spec reviews inspect each task's changes; meaningful findings are corrected and reviewed again.
- Strictly no CI: no GitHub Actions/workflows, Dependabot or repository-linked Cloud Build triggers. Tests, builds and deploys are invoked locally.
