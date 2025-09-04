# RECOVERYOS — Project Kickoff

> Repository: `greta-47/recoveryos` • App: FastAPI • Endpoints: `/healthz`, `/docs`, `/openapi.json`

This document is the **single source of truth** for environment rules, CI/CD posture, security, and contributor workflows.

---

## 1. Non‑Negotiable Rules

- **Python 3.11 everywhere** (local venv, Dockerfile, GitHub Actions). Do **not** change the version without explicit approval.
- **Torch/Triton stability**: keep current Torch pin for CI. If Triton or hashes break CI, **split GPU deps** (see §6) instead of changing the base pin.
- **Ruff-only** formatting & linting:
  ```bash
  ruff format .
  ruff check --fix .
  ```
- **Deterministic dependencies**:
  - Lockfile (`requirements.lock.txt`) is generated **only on Linux + Python 3.11** using `pip-tools` with hashes.
  - **Never** generate or update the lockfile on macOS.
- **Security posture**: non-root containers, read-only FS where possible, strict CSP, local Swagger UI (no CDN), HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
- **Branch hygiene**: small, single-purpose PRs; no unrelated edits; no build artifacts or `.env` files; squash & merge after green CI.

---

## 2. Quickstart (Mac & Linux)

```bash
# Create and activate a Python 3.11 venv
python3.11 -m venv .venv
source .venv/bin/activate

# Base tooling
python -m pip install -U pip wheel

# Install deps from lockfile (never edit lockfile on Mac)
python -m pip install -r requirements.lock.txt --require-hashes

# Bootstrap sanity script (optional but recommended)
bash scripts/bootstrap.sh

# Run the API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Open http://127.0.0.1:8000/docs
```

---

## 3. Lockfile Policy (Deterministic Builds)

Generate the lockfile **only on Linux + Python 3.11**:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.11-slim bash -lc   'python -m pip install -U pip pip-tools==7.4.1 &&    pip-compile --generate-hashes -o requirements.lock.txt requirements.txt'
```

Commit message for lockfile-only updates:

```
chore(ci): regenerate requirements.lock on linux for deterministic hashes
```

---

## 4. GitHub Actions Posture

```yaml
permissions:
  contents: read
  packages: write
  id-token: write
  security-events: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

- **PR workflows**: informational security scans (Trivy, Gitleaks) are **non-blocking**.
- **Main branch**: build, scan, and publish GHCR image.
- Always use `${{ ... }}` syntax in expressions (e.g., `hashFiles`).

---

## 5. Swagger + Strict CSP

- Serve Swagger UI assets **locally** to satisfy strict CSP (no external CDNs).
- Verify `/docs` renders fully with CSP enforced.
- Include an internal `/.well-known` probe (204) for health/csp checks in strict environments.

---

## 6. GPU Dependency Split (If Needed)

If Triton/Torch cause lockfile hash or wheel issues in CI:

- Move GPU-only deps into **`requirements-gpu.txt`** or an install extra `[gpu]`.
- CI installs only base lockfile:
  ```bash
  python -m pip install -r requirements.lock.txt --require-hashes
  ```
- GPU users install separately:
  ```bash
  python -m pip install -r requirements-gpu.txt
  # or
  python -m pip install .[gpu]
  ```

Commit message:
```
chore(deps): move triton/torch to optional [gpu] extra to stabilize CI
```

---

## 7. Branch Naming

- `chore/ci-stability`
- `ci/ghcr-build-push`
- `feat/csp-env-middleware`
- `ops/ruff-py311-bootstrap`
- `chore/bootstrap-scripts`
- `chore/editor-setup`

---

## 8. Contributor Checklist

- [ ] Using **Python 3.11** in a project venv (`.venv`), pinned in VS Code settings.
- [ ] Installed from **`requirements.lock.txt`** (no Mac-generated lockfiles).
- [ ] Ran `ruff format .` and `ruff check --fix .` locally.
- [ ] `scripts/bootstrap.sh` succeeds and `/healthz` returns 200.
- [ ] PR is **small and single-purpose** with clear acceptance criteria.
- [ ] No build artifacts, `.env`, or unrelated changes in the PR.

---

## 9. Known Good Commands

```bash
# Smoke run (Linux/Mac)
uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 2 && curl -fsS http://127.0.0.1:8000/healthz && pkill -f "uvicorn main:app"
```

---

## 10. Support

If you’re blocked by environment issues, post:
- OS + Python version (`python -V`)
- Exact commands run
- Error logs
- Current branch and whether you changed requirements