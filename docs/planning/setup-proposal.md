# Engineering setup proposal

User selected GitHub Issues, authorized Git setup, and retained explicit Task N gates. Repository created by the parent: https://github.com/seekerPrice/highground (public). The parent verified GitHub Actions disabled; local Git is initialized. This document proposes file contents for review; it does not itself activate agent configuration or publish issues.

At initial inspection the workspace contained planning documents only, with no application, agent instructions or domain glossary. Git was subsequently initialized by the parent. The triage skill is installed. Recommend AGENTS.md, the default five labels and one domain context. The planned API/web folders do not justify separate domain contexts.

## Proposed AGENTS.md — complete contents

```markdown
# HighGround agent instructions

## Authority and scope

Follow the user's current instructions and docs/spec/01-build-spec.md. The approved GitHub spec and task issue record resolved decisions; planning drafts do not override the source. If sources conflict, surface the conflict before implementing that behaviour.

Work on one Section 12 task at a time. Wait for the user's Task N instruction and confirmation before advancing. Astra coordinates: brief Sol, inspect actual changes and local checks, return defects to Sol, recheck corrections, then report. Run Matt Standards and Spec reviews against an agreed fixed baseline; keep the two axes distinct and correct/recheck findings.

Use only the Section 5 stack. Keep modules small and typed; validate external and model responses. Avoid abstractions without a current requirement. All Musts must be deployed Thursday 15 October 2026. Shoulds are Friday-only after Tasks 1–17 work on deployed URLs. Stretch is pitch-only.

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
```

## Proposed docs/agents/issue-tracker.md — complete contents

```markdown
# Issue tracker: GitHub

Specs and implementation tickets live in GitHub Issues for seekerPrice/highground. Use the authenticated gh CLI; verify the remote before mutation. Do not create GitHub automation.

Create one parent specification issue and one issue per approved Section 12 task, preserving Task 1–22 numbering and titles. Record the task number independently of GitHub's issue number. Link each task to the spec and its preceding execution gate; use native blocking dependencies when available, otherwise explicit Blocked by references. Shoulds also depend on deployed acceptance of Tasks 1–17 and Friday scheduling.

Read full issue bodies, labels and comments before work. For multiline issue bodies and comments, use a temporary text file with --body-file. Apply ready-for-agent only when scope is resolved; it never overrides the user's Task N authorization gate. Use needs-info for unresolved decisions. Do not close the parent spec just because individual tickets are created.

PRs as a request surface: no.

The user authorized publishing the source spec and original numbered task breakdown. Publish unresolved decisions on affected issues with needs-info; do not treat issue publication as permission to implement or globally block unrelated tasks. Completion comments include acceptance evidence and known limitations. No external messaging beyond the authorized project issue work.
```

## Proposed docs/agents/domain.md — complete contents

```markdown
# Domain docs

Before relevant work, read CONTEXT.md and applicable docs/adr entries if present. Missing documents are not an error; create them lazily when domain terms or architectural decisions are actually resolved.

Use a single context for HighGround. CONTEXT.md is a glossary only: actors, concepts, relationships and explicitly distinguished terms. It contains no implementation plan or technical configuration. Reuse its vocabulary in specs, tickets and tests.

Create an ADR only for a hard-to-reverse decision with a meaningful trade-off that would otherwise surprise a future reader. Flag conflicts rather than silently overriding an ADR. Planning proposals remain proposals until agreed.
```

## Proposed docs/agents/triage-labels.md — complete contents

```markdown
# Triage labels

| Canonical role | Repository label | Meaning |
|---|---|---|
| needs-triage | needs-triage | Evaluate request and scope |
| needs-info | needs-info | Missing decision or information |
| ready-for-agent | ready-for-agent | Scope resolved; still subject to Task N gate |
| ready-for-human | ready-for-human | Human implementation or intervention required |
| wontfix | wontfix | Will not be actioned |
```

## Reviewable setup decisions

GitHub and Task N gates are settled. Recommend activating the proposed AGENTS.md and default labels after the user reviews this draft. The skill asks for the choice of agent-instruction filename when neither exists; AGENTS.md is proposed here, not silently selected. Single-context domain layout needs no extra configuration interview.
