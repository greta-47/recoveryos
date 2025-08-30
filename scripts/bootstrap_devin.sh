#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap_devin] cwd: $(pwd)"
echo "[bootstrap_devin] python: $(python -V || true)"

python -m pip install -U pip wheel >/dev/null 2>&1 || true

if [[ -f "requirements.lock.txt" ]]; then
  echo "[bootstrap_devin] Installing from requirements.lock.txt with --require-hashes"
  python -m pip install --require-hashes -r requirements.lock.txt
elif [[ -f "requirements.txt" ]]; then
  echo "[bootstrap_devin] Installing from requirements.txt"
  python -m pip install -r requirements.txt
else
  echo "[bootstrap_devin] No requirements file found; skipping install."
fi

if command -v ruff >/dev/null 2>&1; then
  ruff format . || true
  ruff check --fix . || true
fi

if [[ -x "scripts/bootstrap.sh" ]]; then
  echo "[bootstrap_devin] Delegating to scripts/bootstrap.sh"
  exec scripts/bootstrap.sh "$@"
else
  echo "[bootstrap_devin] Done (no scripts/bootstrap.sh found)."
fi
