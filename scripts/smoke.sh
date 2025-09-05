#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8000/healthz}"

echo "=== RecoveryOS Smoke Test ==="
echo "Testing endpoint: $URL"

if curl -fsSL "$URL" | grep -q "status.*ok"; then
  echo "✅ PASS: Health check successful"
  exit 0
else
  echo "❌ FAIL: Health check failed"
  exit 1
fi
