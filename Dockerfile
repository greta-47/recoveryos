# ================================
# RecoveryOS API - Production Dockerfile
# Secure, minimal, auditable
# ================================

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

# Minimal OS deps (libgomp for torch; curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Optional: Preload SentenceTransformer model to avoid cold pull at runtime ---
# Build-time toggle: docker build --build-arg PRELOAD_RAG_MODEL=1 ...
ARG PRELOAD_RAG_MODEL=0
ENV RAG_MODEL=all-MiniLM-L6-v2
RUN if [ "$PRELOAD_RAG_MODEL" = "1" ]; then \
      python -c "from sentence_transformers import SentenceTransformer as S; import os; m=os.environ.get('RAG_MODEL','all-MiniLM-L6-v2'); S(m); print(f'Preloaded model: {m}')" ; \
    fi

# Copy app source
COPY . /app

# Ownership to non-root
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root
USER appuser

# --- Healthcheck (curl) ---
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz" || exit 1

# Labels for audit and traceability
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Your Name <you@recoveryos.app>" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

# Expose conventional port (platforms will set $PORT)
EXPOSE 8000

# --- Start (Gunicorn + Uvicorn worker) ---
# WORKERS can be tuned via env; default 1 for small instances
ENV WORKERS=1
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS} --timeout 45 main:app"]
