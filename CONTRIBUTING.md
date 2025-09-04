# Contributing to RecoveryOS

## GitHub Actions Policy

**PR workflows**: Informational scans (non-blocking), but **Lockfile Preflight is Required**.

**Main workflow**: Builds & publishes to GHCR; security scans are blocking.

**Required permissions**:
```yaml
permissions:
  contents: read
  packages: write
  id-token: write
  security-events: write
```

**Trivy/Gitleaks**: vuln-only on PRs, SARIF upload if present.

## Local Development Quickstart

```bash
python -V  # must be 3.11
python -m venv .venv && source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.lock.txt --require-hashes
make fix
make smoke  # starts uvicorn briefly and GETs /healthz
```

## Lockfile Regeneration

```bash
make ci-preflight   # locally simulate the CI preflight diff
make lock           # regenerate on Linux with pip==24.2.1 + pip-tools==7.4.1
```

## GPU Users

Install optional GPU deps outside CI:

```bash
pip install -r requirements-gpu.txt
# or
pip install .[gpu]
```
