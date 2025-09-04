#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] Using Python: $(python -V)"
echo "[bootstrap] Upgrading pip & wheel..."
python -m pip install -U pip wheel

echo "[bootstrap] Installing project dependencies..."
if [[ -f "requirements.lock.txt" ]]; then
  echo "[bootstrap] Installing with --require-hashes from lockfile"
  python -m pip install --require-hashes -r requirements.lock.txt || {
    echo "[bootstrap] Lockfile failed locally, falling back to requirements.txt"
    python -m pip install -r requirements.txt
  }
else
  python -m pip install -r requirements.txt
fi

echo "[bootstrap] Running Ruff (non-blocking)..."
ruff format . || true
ruff check --fix . || true

echo "[bootstrap] Launching dev server..."
# Kill anything on 8000 first
lsof -t -i:8000 | xargs -r kill -9 || true

# Start uvicorn in background
( python -m uvicorn main:app --host 0.0.0.0 --port 8000 > recoveryos.log 2>&1 & )
sleep 2

echo "[bootstrap] Health check:"
if curl -fsSL http://127.0.0.1:8000/healthz; then
  echo -e "\n[bootstrap] ✅ /healthz OK"
else
  echo "[bootstrap] ⚠️ Health check failed. See recoveryos.log for details."
  exit 1
fi
