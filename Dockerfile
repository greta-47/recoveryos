# ================================
# RecoveryOS API - Production (deterministic builds)
# ================================
FROM python:3.11.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root + venv
RUN useradd -m -u 10001 appuser
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy lockfile first to maximize layer cache
COPY requirements.lock.txt /app/requirements.lock.txt

# Deterministic install (hash-verified)
RUN pip install --upgrade pip pip-tools && \
    pip install --no-deps --require-hashes -r /app/requirements.lock.txt

# App code
COPY . /app
RUN chown -R appuser:appuser /app /opt/venv
USER appuser

# Healthcheck (classic-builder safe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,sys,urllib.request; url=f'http://127.0.0.1:{os.environ.get('PORT','8000')}/healthz'; urllib.request.urlopen(url, timeout=2); sys.exit(0)" || exit 1

LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

EXPOSE 8000
ENV WORKERS=1
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS} --timeout 45 main:app"]
