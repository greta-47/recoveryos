#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] Python: $(python --version)"
python -m pip install -U pip

if [[ -f requirements.lock.txt ]]; then
  echo "[bootstrap] Installing locked deps (require-hashes)"
  python -m pip install --require-hashes -r requirements.lock.txt
else
  echo "[bootstrap] Installing from requirements.txt (no hashes)"
  python -m pip install -r requirements.txt
fi

python -m pip install -U ruff

ruff format . || true
ruff check --fix . || true

echo "[bootstrap] Starting app on 0.0.0.0:8000"
exec uvicorn main:app --host 0.0.0.0 --port 8000
