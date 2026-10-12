# Task 1 — implementation brief

Status: implementation, local acceptance and both Matt reviews complete. Issue: https://github.com/seekerPrice/highground/issues/2. Source: docs/spec/01-build-spec.md, Section 12 Task 1; current user decisions override dates and retain Task N gates.

Review baseline: `bb1b098` (committed planning state). Captured workspace HEAD was `64398a5d361fcf9c039fe0432ee54ba2cd0397f9`, a GitButler workspace commit with an identical tree; use the stable underlying commit for Matt review. Parent manages commits and remote updates; Astra coordinates Sol and inspects actual code/tests. No later task is authorized.

## Plan and files

- API: minimal typed FastAPI application in api/main.py exposing GET /healthz; one public-contract test in api/tests. Python 3.12, pinned reproducible dependency declaration/lock, no cloud clients or pretend agent tools.
- Web: Next.js App Router with TypeScript and Tailwind; minimal layout, global styling and blank dashboard page. Package manifest/lock and necessary TypeScript/build configuration only. A readable HighGround title and empty-state shell, no map/counters/data or future-feature controls.
- Infra: one local test script runs relevant API and frontend checks with clear failures; no setup/deploy scripts yet.
- Root: README with exact setup/run/check commands, complete .env.example names from Section 15 with no credentials or hard-coded model IDs, MIT licence, ignore generated dependencies/build outputs without hiding source/config.

## Interfaces

GET /healthz is an unauthenticated local liveness endpoint: HTTP 200, JSON {"status":"ok"}. It does not claim any Google Cloud or Telegram dependency is connected. The frontend root responds HTTP 200 and displays the intentional empty dashboard. No API calls to future endpoints.

## Steps

1. Verify current official dependency documentation/versions and installed runtimes; use the fixed stack.
2. Implement only these files, install declared dependencies and produce reproducible locks.
3. Run the public health contract test and local frontend type/lint/build checks appropriate to the chosen supported versions.
4. Start the actual API and Next development server; verify HTTP responses and inspect the page in a browser.
5. Astra reviews actual code and results; Sol corrects defects and affected checks rerun.
6. Parent creates candidate commit; independent Matt Standards and Spec reviewers inspect the pinned baseline-to-HEAD diff. Correct/review findings before final completion.

## Done when

- A fresh documented local setup runs Python 3.12 API and npm dev dashboard without cloud credentials.
- /healthz passes its public-contract check and real HTTP check.
- Actual browser inspection confirms the blank dashboard renders cleanly; frontend build/checks pass.
- All Section 15 configuration names are represented, secrets absent, licence present, and no prohibited automation or later-task implementation exists.
- Checklist records actual evidence and both review axes; Task 2 remains untouched.

## Pitfalls

Do not run a bootstrap wizard or alter host settings. Do not introduce agents, Telegram handlers, GCP setup, deployment, future mock data, authentication or architecture layers. Do not require fonts/assets from a remote service merely to render the local shell. Keep library versions configurable only where specified: model IDs remain environment configuration. Record missing runtimes honestly and resolve with the available supported local tooling, without changing stack.
