# ================================
# RecoveryOS API - Production Dockerfile
# Secure, minimal, auditable
# ================================

# Use slim Python 3.11 (pinned for reproducibility)
FROM python:3.11.9-slim AS base

# Prevents Python from writing __pycache__, .pyc
ENV PYTHONUNBUFFERED=1
# Ensures logs go to stdout/stderr (critical for container logging)
ENV PYTHONFAULTHANDLER=1

# Create non-root user (security best practice)
RUN adduser --disabled-password --gecos '' appuser

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt && \
    pip install gunicorn uvicorn[standard] && \
    rm -rf /root/.cache/

# Copy only essential app files
COPY main.py ./
COPY agents/ ./agents/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check (matches /healthz endpoint in main.py)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Labels for audit and traceability
LABEL org.opencontainers.image.title="RecoveryOS API"
LABEL org.opencontainers.image.description="AI-powered relapse prevention for addiction recovery"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Your Name <you@recoveryos.app>"
LABEL org.opencontainers.image.source="https://github.com/yourname/recoveryos"

# ================================
# Final Stage (minimal runtime)
# ================================
FROM base AS final

# Expose port (convention, but Render uses $PORT)
EXPOSE 8000

# Start with Gunicorn + Uvicorn (more robust than uvicorn alone)
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 30 main:app"]
