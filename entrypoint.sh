#!/bin/bash
set -euo pipefail

if [ -n "${READONLY_MODE:-}" ]; then
  mkdir -p /tmp/app/logs /tmp/app/cache /tmp/app/run
  export LOG_DIR=/tmp/app/logs
  export CACHE_DIR=/tmp/app/cache
  export RUN_DIR=/tmp/app/run
else
  mkdir -p /app/logs /app/cache
  export LOG_DIR=/app/logs
  export CACHE_DIR=/app/cache
fi

if [ -x /app/prestart.sh ]; then /app/prestart.sh; fi

exec gunicorn -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WORKERS:-1} \
  --timeout ${TIMEOUT:-45} \
  main:app
