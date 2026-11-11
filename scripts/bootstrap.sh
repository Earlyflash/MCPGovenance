#!/usr/bin/env bash
# Prepare the governance toolchain on a GitHub-hosted runner: an isolated venv with pinned-range
# dependencies, and the environment later steps need. Safe to run more than once.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${RUNNER_TEMP:-/tmp}/governance-venv"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$ROOT/requirements.txt"

if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "GOV_PYTHON=$VENV/bin/python"
    echo "GOV_ROOT=$ROOT"
    echo "PYTHONPATH=$ROOT"
  } >> "$GITHUB_ENV"
fi
echo "governance toolchain ready (root: $ROOT)"
