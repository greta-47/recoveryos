# ---------- Builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps just enough to build common wheels (we'll drop these later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# If you use requirements.txt
COPY requirements.txt /app/requirements.txt
RUN python -m venv /opt/venv && . /opt/venv/bin/activate && pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

# ---------- Runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    UVICORN_WORKERS=2

# Copy virtualenv only (no build tools)
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

WORKDIR /app

# Create an unprivileged user and lock down perms
RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser \
    && mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app

USER 10001:10001

# Healthcheck (customize path/port)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read(); print('ok')"

EXPOSE 8000

# NOTE: Enforce read-only root FS and drop capabilities at runtime:
# docker run \
#   --read-only \
#   --tmpfs /tmp:rw,noexec,nosuid \
#   --tmpfs /app/tmp:rw,noexec,nosuid \
#   --cap-drop=ALL \
#   --cap-add=NET_BIND_SERVICE \
#   -e ENV=prod -e ENFORCE_HTTPS=true -e CSP_REPORT_ONLY=false \
#   -p 8000:8000 IMAGE

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
