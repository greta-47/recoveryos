# ================================
# RecoveryOS API — Production (deterministic builds)
# ================================
FROM python:3.11.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1

# System deps (psycopg2, curl for healthcheck, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root + working dir
RUN useradd -m -u 10001 appuser
WORKDIR /app

# Virtualenv to avoid pip-as-root issues
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# --- Deterministic dependency install (from lockfile with hashes) ---
# Copy only the lockfile first to leverage Docker layer cache
COPY requirements.lock.txt /app/requirements.lock.txt
RUN python -m pip install --upgrade pip pip-tools && \
    python -m pip install --no-deps --require-hashes -r /app/requirements.lock.txt

# --- App source ---
COPY . /app
RUN chown -R appuser:appuser /app /opt/venv
USER appuser

# Healthcheck (uses curl, simple & reliable)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" || exit 1

# Metadata
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

EXPOSE 8000
ENV WORKERS=1

# If your app entry is at repo root: main.py -> app
# If it's under a package (e.g., api/main.py), change to api.main:app
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS} --timeout 45 main:app"]
