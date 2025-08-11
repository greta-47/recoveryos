# ================================
# RecoveryOS API - Production Dockerfile
# Secure, minimal, auditable
# ================================

# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

# --- Runtime env ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface \
    HF_HOME=/home/appuser/.cache/huggingface

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Minimal OS deps (torch CPU often needs OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Optional: Preload SentenceTransformer model to avoid cold pull at runtime ---
# Build-time toggle: --build-arg PRELOAD_RAG_MODEL=1 (defaults to 0)
ARG PRELOAD_RAG_MODEL=0
ENV RAG_MODEL=all-MiniLM-L6-v2
RUN if [ "$PRELOAD_RAG_MODEL" = "1" ]; then \
      python - <<'PY'; \
from sentence_transformers import SentenceTransformer; import os; \
m=os.environ.get("RAG_MODEL","all-MiniLM-L6-v2"); SentenceTransformer(m); \
print(f"Preloaded model: {m}") \
PY \
    ; fi

# Copy app source
COPY . /app

# Ownership to non-root
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root
USER appuser

# --- Healthcheck (Python-based; no curl needed) ---
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python - <<'PY' || exit 1
import os, sys, urllib.request
port = os.environ.get("PORT", "8000")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
        sys.exit(0 if r.getcode() == 200 else 1)
except Exception:
    sys.exit(1)
PY

# Labels for audit and traceability
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Your Name <you@recoveryos.app>" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

# Expose conventional port (Render/Heroku use $PORT)
EXPOSE 8000

# --- Start (Gunicorn + Uvicorn worker) ---
# WORKERS can be tuned via env; default 1 for small dynos
ENV WORKERS=1
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS} --timeout 45 main:app"]
