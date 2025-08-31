#!/usr/bin/env bash
set -euo pipefail

echo "=== RecoveryOS Bootstrap ==="
echo "Python version: $(python --version)"

python -m pip install -U pip wheel

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
elif [ -f pyproject.toml ]; then
  pip install -e .
fi

ruff format . || echo "Warning: ruff format issues"
ruff check --fix . || echo "Warning: ruff check issues"

echo "=== Starting RecoveryOS ==="
exec uvicorn main:app --host 0.0.0.0 --port 8000
