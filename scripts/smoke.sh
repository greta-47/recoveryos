#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-/healthz}"
URL="${BASE_URL}${HEALTH_ENDPOINT}"

echo "[smoke] GET ${URL}"

if HTTP_CODE="$(curl -fsSL -o /dev/null -w "%{http_code}" "${URL}")"; then
  echo "[smoke] HTTP ${HTTP_CODE}"
  echo "[smoke] PASS"
  exit 0
else
  code=$?
  echo "[smoke] HTTP ${HTTP_CODE:-unknown}"
  echo "[smoke] FAIL (curl exit ${code})"
  exit "${code}"
fi
