# Task22 dashboard candidate and refinement

This frontend slice uses the frozen `OutcomeSummary` contract at public `GET /api/outcomes`. It changes only dashboard UI/styles, the exact public proxy allowlist, a typed feedback parser/component, focused tests and sanitized preview fixtures. Shared backend ownership belongs to the other execution lane. It is not full Task22 acceptance.

## Design critique and implementation

Before editing, the owner read `dashboard-polish-plan.md`, frontend-design skill, web/AGENTS.md, and installed Next16.4 client-components/lazy-loading documentation. The plan's geographic map/activity focal point fits a neighbourhood response board; another equally weighted metric grid would compete with it. The refinement therefore retains bundled Source Sans3, rain paper/harbour ink/river teal, adds section anchors, compacts the measured-action strip and uses a chronological activity rail. Recovery sections remain separate from source status; owner feedback uses a response ledger plus small actual-history plots with equivalent tables. No font, chart or component dependency was added.

New CSS is scoped to `.dashboard-shell`. Report media, full receipt hashes/bytes, capability handling and print rules are untouched. Long names wrap, tables scroll within their own regions and navigation/controls retain visible keyboard focus. Desktop recovery columns become sequential at1100px; map/feed and calibration rows stack below900px; feedback and navigation fit narrow layouts without a forced wide chart. Actual320/390/tablet/desktop rendering is still root-owned verification, not inferred from these rules.

## Boundary and meanings

The parser rejects extra/private fields, real provenance, inconsistent response totals, invented known scope for unavailable data and excessive calibration history. Null/unavailable is never zero. Five answers and one missing response remain visibly distinct. Accepted prompts, virtual prompts, seeded prompts, uncertain sends and fixture responses are separately labelled. History shows bounded synthetic targeting decisions, not accuracy. Fixed official/Danger/check radii do not change; map circles and activity text explicitly show base event radius rather than claiming universal effective coverage.

`outcomes-available.json`, `outcomes-empty.json` and `outcomes-unavailable.json` under `web/tests/fixtures` are disposable UI fixtures. Available has five explicitly seeded responses, one unknown and zero Telegram acceptances, plus a labelled seeded0.9× decision. Empty has known scope but no confirmed episodes; unavailable has null scope/generation/coverage. None proves actual endpoint, job, message or calibration-store acceptance.

## Observed checks and limits

Observed RED: the public outcomes GET returned404 through the existing proxy. After adding only the exact GET path, it returned200 and forwarded neither bearer nor cookies. A controlled old-wording mutation outside the repo also failed the formatter regression: seeded history could not be called accepted-alert responses. The corrected component uses eligible responses and explicitly states that seeded records do not establish Telegram acceptance. New interfaces initially failed because the new module did not exist; that is not a deployed defect. Current focused feedback tests: five passed, zero skips in0.120s. They cover synthetic trend, private/real/count rejection, exact GET/credential stripping, seeded fixture attribution and empty/unknown labels.

Existing complete frontend test run plus the first three feedback cases passed31 tests, zero skips in10.222s. The later added fixture and seeded-label cases passed in the focused rerun. Direct `tsc --project web/tsconfig.json --noEmit --incremental false` and lint both exited0, with no generated Next artifacts. No production build, server restart, SDK/model call or dependency/lock change occurred. Root owns the next build, actual responsive/keyboard/reduced-motion review and protected report/PDF regression. Actual backend feedback route and analytics are separately pending integration evidence.
