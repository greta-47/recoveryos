# syntax=docker/dockerfile:1.7-labs
###############################################
# RecoveryOS API — Elite Multi-Stage Dockerfile
# - Deterministic deps (lockfile if present)
# - BuildKit cache for blazing fast pip installs
# - Small, secure runtime (non-root)
# - Healthcheck
# - Gunicorn (UvicornWorker) for prod-grade serving
###############################################

############################
# Stage 1: builder (wheels)
############################
FROM python:3.11-slim AS builder

# Fewer surprises & faster failures
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps only for building wheels (no runtime bloat)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Copy dependency manifests (use lockfile if present; fall back to requirements.txt)
# We copy both to maximize cache hit, but install conditionally.
COPY requirements.txt /wheels/requirements.txt
COPY requirements.lock.txt /wheels/requirements.lock.txt

# Optional feature-specific requirements (installed only if files exist)
COPY requirements-dev.txt /wheels/requirements-dev.txt
COPY requirements-ml.txt  /wheels/requirements-ml.txt
COPY requirements-db.txt  /wheels/requirements-db.txt
COPY requirements-auth.txt /wheels/requirements-auth.txt

# Upgrade pip toolchain first (cached)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel pip-tools

# Build wheels for deterministic install later (prefer lockfile)
# You can toggle USE_LOCK at build time: `--build-arg USE_LOCK=1`
ARG USE_LOCK=1
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "${USE_LOCK}" = "1" ] && [ -f requirements.lock.txt ]; then \
        pip wheel --wheel-dir=/wheels/dist --require-hashes -r requirements.lock.txt ; \
    else \
        pip wheel --wheel-dir=/wheels/dist -r requirements.txt ; \
    fi

# Optional extras (only if files exist)
ARG INSTALL_DEV=0
ARG INSTALL_ML=0
ARG INSTALL_DB=0
ARG INSTALL_AUTH=0
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "${INSTALL_DEV}" = "1" ] && [ -f requirements-dev.txt ]; then pip wheel -w /wheels/dist -r requirements-dev.txt ; fi && \
    if [ "${INSTALL_ML}"  = "1" ] && [ -f requirements-ml.txt  ]; then pip wheel -w /wheels/dist -r requirements-ml.txt  ; fi && \
    if [ "${INSTALL_DB}"  = "1" ] && [ -f requirements-db.txt  ]; then pip wheel -w /wheels/dist -r requirements-db.txt  ; fi && \
    if [ "${INSTALL_AUTH}"= "1" ] && [ -f requirements-auth.txt ]; then pip wheel -w /wheels/dist -r requirements-auth.txt ; fi


############################
# Stage 2: runtime (slim)
############################
FROM python:3.11-slim AS runtime

# Secure, predictable Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal runtime deps only (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user early (stable UID for K8s/OPA policies)
RUN useradd -m -u 10001 appuser

# Copy prebuilt wheels and install (deterministic, air-gapped friendly)
COPY --from=builder /wheels/dist /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir /wheels/*

# Copy application code (only what you need)
# If you have a pyproject or package layout, adjust as necessary.
COPY . /app
RUN chown -R appuser:appuser /app

USER appuser

# App runtime env (override in Compose/Cloud)
ENV APP_NAME="RecoveryOS API" \
    APP_VERSION="0.1.0" \
    PORT=8000 \
    WORKERS=1 \
    TIMEOUT=45

# Healthcheck (platforms can auto-restart on failures)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

EXPOSE 8000

# Gunicorn with Uvicorn workers for production-grade serving
# NOTE: If your ASGI app path changes (e.g., package.module:app), update below.
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers ${WORKERS} --timeout ${TIMEOUT} main:app"]

