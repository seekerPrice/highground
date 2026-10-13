# Task 19 local policy implementation verification

Implementation baseline: `831c3661f01336c6d35b9ad6997a53f542ce8d3a`. Application source frozen for root's isolated acceptance snapshot on 2026-10-13. This note is evidence, not a replacement for the approved source or an acceptance claim.

## Implemented contract

Owner-only `/policy` discloses default deletion of HighGround's stored copy before an upload is authorized. Explicit Keep must precede the first document; it applies only to successful extraction. One PDF or up to five sequential policy photos, at most 20 MB combined, use existing ingestion/hash/ledger boundaries. Photos require Done. Cancel and failed extraction initiate durable deletion even with Keep. Original identities, hashes, dates, locations and frozen inventory remain immutable on replay.

Configured Pro receives originals only in copied transient ADK request content. A before-persistence response callback retains only locally validated bounded fields/quotes; invalid output becomes a sanitized unknown response. Model requests and catalog generation contain no hardcoded model ID. Recognizable English/Malay inclusion/exclusion checks are intentionally conservative; unsupported, contradictory or conditional evidence cannot establish yes/no. Quoted MYR stock/contents limits and excess labels are required; building cover, premium, ambiguous currency/scope and percentage excess cannot become invented MYR cover. Expiry/current coverage and replacement-price comparison remain qualified; excess is not added to cover.

The default-success completion transaction atomically publishes permitted fields and marks originals pending deletion, avoiding a crash gap. A private permanent media gate plus exact-owned-generation zero-byte storage fence prevents delayed create-only PUT from recreating policy bytes. Exact old-generation absence is checked; unrelated replacements are untouched. The empty marker is metadata, never an available policy or authenticity proof. Crash recovery uses only reserved upload identity, expected hash and owned object metadata, never a Telegram re-download. Pending ledger/deletion work remains resumable.

A kept copy has owner-bound `policy:copy:<intake-id>:<index>` controls and an explicit delete-copy control. Copy sends are private bounded Bot API multipart uploads, with generated filenames and no public/signed URL. After the inbox enters sending, a final owner/retention/Danger recheck precedes transport. Pre-send failures remain retryable; an attempted ambiguous send remains uncertain. General registered-recipient lookup supplies risk-only guards; policy data and mutations remain owner-only.

`/jobs/resume-pending` includes a bounded `policy_deletions` stage under existing Scheduler authorization. It is manual recovery; no running schedule is claimed. Root's existing README manual invocation uses a bearer header rather than a URL token.

Dashboard `policy_coverage` is optional and nullable, with `policy_note`. Values cover only the verified synthetic shop scope. Missing/unclear/expired policies and unknown stock amounts are separate from the explicit yes/no denominator. Private quotes, insurer, owner identifiers, original IDs and policy copies never enter this aggregate. A missing source is unavailable, not zero.

## Observed checks

- **65 pure cases:** final command covering policy models, agent response boundary, generation interleavings, PDF validator, factory, localized replies, callback races and protected injected resumer: 65 passed, zero skips, 3.86 s, exit 0. One existing upstream Starlette/httpx deprecation warning.
- **14 actual Firestore cases:** four protected public-webhook cases, eight service lifecycle cases, and two gateway cases using the existing ingestion code. Originals/model/GCS/ledger transports were explicitly fake in these tests. The final combined run also included seven pure checks: 21 passed, zero skips, 26.57 s, exit 0. All exact unique-prefix collections and owned Firestore clients were cleaned; no global records or services changed.
- Default completion crash: actual Firestore RED 1 failure, then atomic pending marking GREEN. A new service resumed deletion without rerunning the model.
- Post-PUT receipt validation: actual public service RED 1 failure (collecting/orphaned object), then durable failure/retire/recover/delete GREEN.
- Old retryable flood photo followed by new policy context: actual protected handler RED 1 failure (photo routed into policy), then deterministic original photo-report binding priority GREEN. A new unbound photo still enters policy context. No media scan was added.
- Copy-final-guard experiment: a temporary isolated API source copy bypassed only `recheck_copy`; 4 failures in 2.76 s, exit 1 (deletion, ownership revocation, Danger, transient failure all sent private bytes). Current source: 4 passed in 2.27 s, exit 0. Temporary source removed; shared/live runtime never changed for this experiment.
- Factory ownership flag shadow: real factory with fake owned clients produced a bool-not-callable RED; renamed lifecycle flag GREEN. Clients close without shadowing authorization.
- Quote parsing: natural sentence-final periods and malformed partial grouping produced RED; whole numeric-token validation GREEN. Fire-only/contradictory/conditional positive and negative coverage, unqualified excess, non-MYR, building/premium and stale partial baseline cases are covered.
- Official SDK metadata-copy semantics: root's actual GCS repeat-fence RED exposed `Blob.metadata` getter copying. The fake was corrected to match the SDK; RED 2 failures, then one complete metadata assignment GREEN. Offline official Blob property behavior is also exercised.
- Never-PUT marker followed by ledger outage: pure generation RED 2 failures, then owned zero marker recognition GREEN; actual Firestore gateway resume passes without a file re-download. Nonempty marker impostors and unrelated replacement generations fail closed.
- Configured Flash generated exactly 31 new policy keys for each of seven non-English catalogs. Key sets/placeholders validated; all pre-existing strings, committed Danger variants and `_reviewed` flags preserved exactly. Provider output is outside Git at `outputs/highground/task18-19-policy-translations`. Native-language review remains pending. All eight catalogs' longest policy summaries and callback identities are bounded; simulations and review notices remain visible.

The policy collection contains **79 cases: 65 pure + 14 Firestore**. Future Task 20 cases are separate and must not be counted as Task 18/19 acceptance.

## Parent-owned acceptance evidence and remaining limits

Root reported a successful configured Pro synthetic PDF extraction in 5.428 s, with permitted exact fields and five ADK events containing neither original inline bytes nor the synthetic full-document canary. Root separately verified actual isolated GCS owned generation deletion, complete empty marker metadata, repeat/no-PUT fencing and unrelated replacement preservation, then cleaned its unique bucket. These are model/storage component evidence, not the complete Telegram lifecycle.

PDF application limits are one parser, 100 pages, 20 MB source, CPU 2 s, parent deadline 3 s and 256 MiB Linux address space. macOS uses bounded sampled RSS with kill/reap on missing measurement or threshold; sampling can overshoot and is **not** a hard address-space cap. Real valid/encrypted/malformed/page-cap and deterministic kill/reap tests pass. Root observed production Linux child CPU soft/hard 2 s and AS soft/hard 268435456, with valid PDF parse exit 0.

Root's first live default-delete PDF journey accepted disclosure, stored one original, then failed with deletion pending. Root subsequently reported the actual factory/resumer path recovered that job (scanned 1, completed 1, pending 0), preserving the owned empty marker and privacy. The original failure had storage done, ledger pending and no assessment; its SDK cause was not captured, so a transient explanation remains a hypothesis. Complete fresh default/Keep/private-copy/delete acceptance remains open; no full Task 19 acceptance is claimed here. Source remains frozen while root performs the newly authorized fresh upload.

Deletion statements refer only to HighGround's stored original generation. They do not claim erasure of the Telegram upload/message, external provider processing, storage soft-delete/backups, or every external copy. Cloud/deployed acceptance, hosted scheduling, and native translation review remain explicitly pending.

## Independent review correction batch after the 432-case candidate

Only `api/policy_models.py`, its model/agent tests and this note changed. No model request/schema, ingestion, storage, webhook, catalogs, dependencies or frontend changes; no SDK/model probes were run.

Three unique findings were reproduced: contradictory flood inclusion/exclusion could be classified as no; a separate MYR metadata claim could turn an EUR/bare quoted number into RM; and conditional/alternative excess could be presented as one known amount. Initial direct-domain plus external-wire checks produced **12 failures in 1.48 s**, exit 1. Root's same-scope qualified-inclusion/special-perils and mixed-currency examples produced **8 further failures in 1.52 s**, exit 1.

Negative coverage now applies the same supported affirmative recognition as positive coverage, ignoring recognized negated matches while refusing contradictory clauses. Quantified money requires exactly one quoted numeric value bound directly to RM/MYR/ringgit; generic currency metadata cannot supply the amount's currency. Conflicting currency declarations or adjacent code labels fail closed without adding a currency registry. Conditional or alternative excess wording, and multiple quoted numeric values, cannot become one fixed excess.

Each rejected external wire response is checked through the actual sanitization callback: it produces unclear coverage, null monetary fields and no quote, then an unknown synthetic aggregate with a zero known denominator and null percentage/estimate. Valid adjacent/spaced RM, MYR sentence-final amounts, the existing Pro affirmative fields/excess/expiry, and canonical negative wording remain accepted.

**24 new cases**: ten domain rejection cases, ten wire/sanitized-fallback/aggregate cases and four valid controls. Models plus agent: **57 passed in 1.38 s**. Full pure policy set: **89 passed, zero skips, 4.14 s, exit 0**, with one existing upstream Starlette/httpx deprecation warning. Policy collection is now **103 cases = 89 pure + 14 unchanged Firestore cases**. This is a +24 delta from the parent's 432-case candidate; the expected API count is 456 before any separate Task 20 work. Parent owns the final full gate, runtime/image refresh and both independent rechecks.

## Remaining independent recheck correction

The interrupted parent gate stopped after 135 passing API cases and is not acceptance. Both original review axes identified remaining scope examples: a negated base clause followed by covered/included endorsement wording, and a fixed-looking excess followed by an unrecognized condition.

Observed **8 RED failures in 1.74 s**, exit 1: two endorsement quotations and `when unoccupied`/`during closure` excess quotations, each exercised through direct domain validation and actual wire sanitization/unknown aggregate behavior.

The no-cover guard now removes recognized explicitly negated affirmative phrases, then conservatively refuses any remaining affirmative coverage token. It does not require flood to be repeated in the endorsement clause. Canonical `Flood is not covered.` remains valid; unrelated affirmative insured-peril context may conservatively become unknown.

Known excess uses a whole-quote allowed shape: an existing excess/deductible label, optional colon/is/of, one existing RM/MYR/ringgit amount and optional punctuation. Any trailing conditions or unrecognized context remain unknown, avoiding an expanding condition blacklist. Existing actual Pro `Excess MYR1,000.` and prefix/suffix currency controls remain valid. No model request/schema, shared service, translation, dependency or SDK/model change was made.

**11 further cases**: four rejection variants at both domain and sanitizer/aggregate boundaries, plus three valid fixed-excess shapes. Models/agent: **68 passed in 1.64 s**. Full pure policy set: **100 passed, zero skips, 4.35 s, exit 0**, with the same upstream Starlette/httpx warning. Policy collection is **114 = 100 pure + 14 unchanged Firestore cases**. Cumulative delta is +35 from the 432-case candidate; expected API count is 467, with separate Task 20 cases excluded. Both original independent review axes must clear the corrected snapshot before parent reruns the full gate/image.
