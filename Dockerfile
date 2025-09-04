# syntax=docker/dockerfile:1.7
# ================================
# RecoveryOS API — Elite Production (deterministic, multi-stage)
# ================================

########## Stage 1: build wheels (no runtime bloat) ##########
FROM python:3.11.9-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps only (removed from runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Prefer lockfile with hashes; fall back to requirements.txt if needed
COPY --chown=root:root requirements.txt /wheels/requirements.txt
COPY --chown=root:root requirements.lock.txt /wheels/requirements.lock.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    sh -euc 'python -m pip install 'pip==24.2.1' setuptools wheel 'pip-tools==7.4.1' && \
             if [ -s /wheels/requirements.lock.txt ]; then \
               echo ">> Using requirements.lock.txt (hash-locked)"; \
               pip wheel --wheel-dir=/wheels/dist --require-hashes -r /wheels/requirements.lock.txt; \
             else \
               echo ">> Using requirements.txt"; \
               pip wheel --wheel-dir=/wheels/dist -r /wheels/requirements.txt; \
             fi'

########## Stage 2: slim runtime ##########
FROM python:3.11.9-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_NAME="RecoveryOS API" \
    APP_VERSION="0.1.0" \
    PORT=8000 \
    WORKERS=1 \
    TIMEOUT=45 \
    TMPDIR=/tmp/app

# Minimal runtime deps only (curl for healthcheck, libpq5 for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libpq5 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/tmp/*

# Non-root user early so we can --chown on COPY
RUN useradd -m -u 10001 appuser

# Create directories for read-only filesystem support
RUN mkdir -p /tmp/app /var/log/app /var/cache/app /app/logs /app/cache \
 && chown -R appuser:appuser /tmp/app /var/log/app /var/cache/app /app/logs /app/cache

WORKDIR /app

# Install prebuilt wheels, then remove build artifacts (same layer)
COPY --from=builder --chown=appuser:appuser /wheels/dist /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    sh -euc 'pip install --no-cache-dir /wheels/* && rm -rf /wheels'

# App source
COPY --chown=appuser:appuser . /app

# Create entrypoint script for read-only filesystem support
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

# Healthcheck (simple & reliable)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# Metadata
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery (Hardened)" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/greta-47/recoveryos" \
      security.scan="trivy" \
      security.non-root="true" \
      security.readonly="supported" \
      security.hardened="true" \
      security.build-tools="removed"

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

