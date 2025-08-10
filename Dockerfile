# ================================
# RecoveryOS API - Production Dockerfile
# Secure, minimal, auditable
# ================================

# Base image (pin for reproducibility)
FROM python:3.11.9-slim AS base

# --- Runtime env ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user/group with stable IDs
RUN addgroup --system --gid 10001 appuser && \
    adduser  --system --uid 10001 --ingroup appuser appuser

# System deps: curl for HEALTHCHECK, tini to handle PID 1 properly
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl tini && \
    rm -rf /var/lib/apt/lists/*

# Working dir
WORKDIR /app

# Copy only requirements first for better build caching (if present)
# If you switch to pyproject.toml, adjust this section.
COPY --chown=appuser:appuser requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then \
      pip install --no-compile -r /app/requirements.txt && \
      pip install --no-compile gunicorn uvicorn[standard]; \
    else \
      pip install --no-compile gunicorn uvicorn[standard]; \
    fi

# Copy the entire application (use a .dockerignore to keep it lean)
COPY --chown=appuser:appuser . /app

# Switch to non-root
USER appuser

# Health check endpoint must exist in main.py
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# OCI labels
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Your Name <you@recoveryos.app>" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

# ================================
# Final Stage (runtime)
# ================================
FROM base AS final

# Network
EXPOSE 8000
ENV PORT=8000

# Use tini for proper signal handling and zombie reaping
ENTRYPOINT ["/usr/bin/tini", "--"]

# Launch Gunicorn with Uvicorn workers
# Tweak WORKERS/TIMEOUT via env on your platform
CMD ["sh", "-c", "gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WORKERS:-1} \
  --timeout ${TIMEOUT:-30} \
  --access-logfile - \
  --error-logfile -"]
