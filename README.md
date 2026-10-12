# HighGround

Flood preparation and recovery for small shops. This repository currently contains
Task 1: a local FastAPI liveness endpoint and an empty Next.js dashboard. Cloud
services, Telegram and flood observations are not connected yet.

## Requirements

- Python 3.12 (tested with 3.12.13)
- Node.js 24 and npm 11 (tested with 24.14.0 and 11.9.0)

Run these commands from the repository root. If `python3.12` is not on your PATH,
use its installed absolute path instead.

## Install

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.txt
npm --prefix web ci
```

Both dependency files pin the installed versions. `api/requirements.in` lists
direct Python dependencies; `api/requirements.txt` locks their full dependency
set. `web/package-lock.json` locks frontend dependencies. No credentials or
`.env` file are required for this scaffold. `.env.example` records the source
spec's configuration names for later tasks; model IDs are intentionally blank.

## Run locally

In one terminal:

```sh
.venv/bin/python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
npm --prefix web run dev
```

Open [the dashboard](http://localhost:3000). It should show HighGround, Dashboard,
and an empty state saying observations and shop activity are not connected yet.
If port 3000 is occupied, Next.js prints the alternative local URL. You can
choose a port explicitly with `npm --prefix web run dev -- --port 3001`.

Check the API:

```sh
curl --fail http://localhost:8000/healthz
```

Expected: HTTP 200 with `{"status":"ok"}`. This endpoint reports process
liveness only. It does not check external services.

## Verify locally

```sh
./infra/test.sh
```

This runs the API's public HTTP contract test, frontend lint, TypeScript checks
and the production build. Each failure stops the script. Lint uses the official
ESLint and typescript-eslint recommended rules. The blank shell has no client
hooks or specialised Next.js features requiring additional framework rules. To run the built web
app after verification, stop its development server, then run:

```sh
npm --prefix web run start
```

All verification runs locally. The repository has no GitHub Actions, Dependabot
or repository-connected Cloud Build triggers.

## Layout

- `api/`: FastAPI app, health test and pinned dependencies.
- `web/`: Next.js App Router, TypeScript and Tailwind dashboard shell.
- `infra/`: local verification script.
- `docs/spec/01-build-spec.md`: authoritative build spec.
- `docs/planning/approved-decisions.md`: approved amendments and task gates.

Later tasks are implemented only after the user's next Task N instruction.

## Licence

MIT; see [LICENSE](LICENSE).
