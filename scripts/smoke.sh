#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "[smoke] Launching app..."
uvicorn main:app --host "$HOST" --port "$PORT" --log-level warning &
PID=$!
trap 'kill $PID || true' EXIT

sleep 3

echo "[smoke] GET /healthz"
curl -fsS "http://$HOST:$PORT/healthz" -o /dev/null

echo "[smoke] OK"
kill $PID || true
trap - EXIT
