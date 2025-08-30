#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] Python version:"
python --version

python -m pip install --upgrade pip wheel

if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
  pip install .
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check . || true
  ruff format --check . || true
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
