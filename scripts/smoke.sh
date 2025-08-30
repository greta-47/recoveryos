#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://127.0.0.1:8000/healthz}"
echo "[smoke] GET $URL"
curl -fsSL "$URL" >/dev/null
echo "[smoke] OK"
