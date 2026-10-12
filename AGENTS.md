# HighGround agent instructions

## Authority and scope

Follow the user's current instructions and the source at docs/spec/01-build-spec.md, with approved amendments in docs/planning/approved-decisions.md. The GitHub spec and task issues record resolved decisions; planning drafts do not override the source. If sources conflict, surface the conflict before implementing that behaviour.

Work on one Section 12 task at a time. Wait for the user's Task N instruction and confirmation before advancing. Astra (gpt-6-astra) coordinates 6.1 Sol (gpt-6.1-sol): brief Sol, inspect actual changes and local checks, return defects to Sol, recheck corrections, then report. Run Matt Standards and Spec reviews against an agreed fixed baseline; keep the two axes distinct and correct/recheck findings.

For ordinary project decisions presented with a recommended option, the user authorizes adopting that option after five minutes without a reply. Record the choice and its reasoning. This does not remove explicit Task N gates or supply missing credentials or facts. Do not delay routine choices that are already authorized.

Use only the Section 5 stack. Keep modules small and typed; validate external and model responses. Avoid abstractions without a current requirement. Calendar allocations are targets, not earliest-start restrictions: finish and advance earlier when the user authorizes the next task. All Musts, including Task 15's dashboard, target deployment by Thursday 15 October 2026. Shoulds may start earlier than Friday only after Tasks 1–17 work on deployed URLs and the user authorizes the task. Keep task order and Task N gates. Stretch is pitch-only. Earlier progress does not extend the code-freeze or submission deadlines.

## Safety, honesty and privacy

Danger uses committed fixed templates, never runtime generation; permitted placeholders and no-destination fallback follow the approved spec. No stock/video requests at Danger. Vehicle deadline is earlier than stock. Do not claim a route/site is safe, a message is genuine, or a hash proves recording authenticity. Use sourced destination labels, estimates, confidence and translation-review status as specified without adding content outside the approved Danger template.

Reject stale/error observations for current alerts. Label simulations and unavailable sources. Preserve downloaded upload bytes and append-only evidence records, subject to the explicitly approved policy-document retention exception. Keep private media private and exclude recipient identifiers from public output.

## Local verification and deployment

No .github/workflows, GitHub Actions, Dependabot, other GitHub-hosted automation or repository-connected Cloud Build triggers. Tests, lint, builds and deployment run locally. Manually invoked source deployment is allowed. GitHub Issues and the public source repository are allowed.

Never commit secrets. Use environment variables/Secret Manager and safe example values. Model IDs are configurable. Run meaningful tests for parsers, deterministic triage, fixed Danger output, lift-first ranking, hashing and idempotent confirmations; validate the deployed end-to-end journey at its specified gates. Report actual results and limitations, never assumed success.

## Agent skills

### Issue tracker

Specs and task tickets live in GitHub Issues for seekerPrice/highground. See docs/agents/issue-tracker.md.

### Triage labels

Use the default five canonical labels. See docs/agents/triage-labels.md.

### Domain docs

Use one domain glossary and relevant ADRs. See docs/agents/domain.md.
