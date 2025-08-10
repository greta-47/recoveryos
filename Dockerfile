# ================================
# RecoveryOS API - Production Dockerfile
# Secure, minimal, auditable
# ================================

# Use slim Python 3.11 (pinned for reproducibility)
FROM python:3.11.9-slim AS base

# --- Runtime env ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user (security best practice)
# UID/GID 10001 avoids clashes on some PaaS
RUN addgroup --system --gid 10001 appuser && \
    adduser  --system --uid 10001 --ingroup appuser appuser

# System packages needed at runtime (curl for HEALTHCHECK)
# tini is a tiny init to handle PID 1 signals & zombies correctly
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl tini && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt /app/requirements.txt

# Install Python deps (gunicorn + uvicorn workers included)
RUN pip install --no-compile -r requirements.txt && \
    pip install --no-compile gunicorn uvicorn[standard]

# Copy only essential app files
# (adjust paths if your package layout changes)
COPY --chown=appuser:appuser main.py /app/main.py
COPY --chown=appuser:appuser agents/ /app/agents/

# Switch to non-root user
USER appuser

# Health check (expects /healthz in main.py)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

# Labels for audit and traceability
LABEL org.opencontainers.image.title="RecoveryOS API" \
      org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Your Name <you@recoveryos.app>" \
      org.opencontainers.image.source="https://github.com/yourname/recoveryos"

# ================================
# Final Stage (minimal runtime)
# ================================
FROM base AS final

# Expose port (Render/Heroku will set $PORT; default 8000 for local)
EXPOSE 8000
ENV PORT=8000

# Use tini as entrypoint to reap zombies & forward signals to gunicorn
ENTRYPOINT ["/usr/bin/tini", "--"]

# Start Gunicorn + Uvicorn worker (robust vs. raw uvicorn)
# Workers=1 is fine for async; bump if you have CPU headroom
CMD ["sh", "-c", "gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WORKERS:-1} \
  --timeout ${TIMEOUT:-30} \
  --access-logfile - \
  --error-logfile -"]
