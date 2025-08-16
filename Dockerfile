# syntax=docker/dockerfile:1.7
###############################################
# RecoveryOS API — Elite, Stable, Production
# - Stable BuildKit syntax (no labs extensions)
# - Multi-stage: build wheels, slim runtime
# - Non-root, healthcheck, gunicorn+uvicorn
# - COPY --chown, remove build artifacts
###############################################

############################
# Stage 1: builder (wheels)
############################
# Pin version; optionally pin digest for full immutability.
FROM python:3.11.9-slim AS builder
# Example digest pin (optional): 
# FROM python:3.11.9-slim@sha256:aaaaaaaa... AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps only (kept out of runtime image)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Core deps (determinism comes from pinned requirements.txt)
COPY requirements.txt /wheels/requirements.txt

# Upgrade pip toolchain (cached) and build wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    sh -euc 'python -m pip install --upgrade pip setuptools wheel && \
             pip wheel --wheel-dir=/wheels/dist -r /wheels/requirements.txt'


############################
# Stage 2: runtime (slim)
############################
FROM python:3.11.9-slim AS runtime
# Optional digest pin:
# FROM python:3.11.9-slim@sha256:aaaaaaaa... AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_NAME="RecoveryOS API" \
    APP_VERSION="0.1.0" \
    PORT=8000 \
    WORKERS=1 \
    TIMEOUT=45

# Minimal runtime deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Create non-root early so we can --chown on COPY
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Install prebuilt wheels; cleanup wheels in same layer
COPY --from=builder --chown=appuser:appuser /wheels/dist /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    sh -euc 'pip install --no-cache-dir /wheels/* && rm -rf /wheels'

# Copy application code as appuser (no root-owned files)
COPY --chown=appuser:appuser . /app

USER appuser

# Tiny ENTRYPOINT for clean signal handling (PID 1) and future hooks
# (You could also keep a separate file; embedding here avoids extra files.)
RUN sh -euc 'cat > /app/entrypoint.sh <<\"SH\" \n\
#!/usr/bin/env sh\n\
set -euo pipefail\n\
# Prestart hook: run DB migrations, generate assets, etc. if needed\n\
if [ -x /app/prestart.sh ]; then /app/prestart.sh; fi\n\
# Exec to hand off PID 1 so signals (SIGTERM) reach gunicorn properly\n\
exec gunicorn -k uvicorn.workers.UvicornWorker \\\n\
  --bind 0.0.0.0:${PORT} \\\n\
  --workers ${WORKERS} \\\n\
  --timeout ${TIMEOUT} \\\n\
  main:app\n\
SH\n\
&& chmod +x /app/entrypoint.sh'

# Healthcheck (platform can auto-restart on failures)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
