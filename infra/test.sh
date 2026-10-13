#!/usr/bin/env bash
# Local verification only; no hosted automation.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

mode=full
if [[ $# == 1 && "$1" == "--unit" ]]; then mode=unit
elif [[ $# != 0 ]]; then echo "Usage: ./infra/test.sh [--unit]" >&2; exit 2; fi

if [[ ! -x .venv/bin/python ]]; then
  echo "Create .venv and install api/requirements.txt first; see README.md." >&2
  exit 1
fi
if [[ ! -d web/node_modules ]]; then
  echo "Install web dependencies with npm ci first; see README.md." >&2
  exit 1
fi

.venv/bin/python -m unittest discover -s infra/tests -v
.venv/bin/python infra/local_gate.py "$mode"
npm --prefix web run test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
