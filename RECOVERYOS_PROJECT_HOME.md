
# RecoveryOS — Project Home

> Central hub for all chats, rules, links, tasks, and templates. Keep this pinned in your ChatGPT **Project**.

---

## 1) How to set up this Project in ChatGPT
1. Click **New → Project**.
2. Name it **“RecoveryOS Development”**.
3. Add these initial **chats** (new conversations inside the project):
   - **RecoveryOS — CI/CD & GitHub Actions**
   - **RecoveryOS — Repo Architecture**
   - **RecoveryOS — Devin Bot Integration**
   - **RecoveryOS — Security & Compliance**
   - *(Optional)* **RecoveryOS — Product & Roadmap**
4. Paste the section **“Pinned Working Rules”** below into the Project **About** field (or the top message of your first chat).
5. Upload any screenshots, logs, and PDFs into the **relevant chat**, not the general project chat.

---

## 2) Pinned Working Rules (paste into Project About)
**Non‑negotiables**
- **Python 3.11 everywhere** (local venv, Docker, GitHub Actions). Do not change without explicit approval.
- **Torch pin stays fixed** for CI stability. If CI breaks due to Triton/hashes, split GPU deps to `requirements-gpu.txt` instead of changing the base pin.
- **Ruff‑only** lint/format: `ruff format .` then `ruff check --fix .` before commits.
- **Deterministic lockfile** on **Linux + Python 3.11** only (never on Mac):
  ```bash
  docker run --rm -v "$PWD":/app -w /app python:3.11-slim bash -lc   'pip install 'pip==24.2' 'pip-tools==7.4.1' && pip-compile --generate-hashes -o requirements.lock.txt requirements.txt'
  ```
- **Security posture**: non-root Docker, strict CSP, local Swagger UI (no CDN), HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
- **Branch hygiene**: small, single‑purpose PRs; no unrelated edits; no build artifacts or .env files.

**Branch name patterns**
- `chore/ci-stability`, `ci/ghcr-build-push`, `feat/csp-env-middleware`, `ops/ruff-py311-bootstrap`, `chore/bootstrap-scripts`, `chore/editor-setup`

**GitHub Actions permissions**
```yaml
permissions:
  contents: read
  packages: write
  id-token: write
  security-events: write
```
- Trivy/Gitleaks: vuln-only and **non-blocking**; PR workflows run scans for information, main does build/publish.

---

## 3) Project Overview (share with collaborators)
**Repo:** `greta-47/recoveryos` (FastAPI app with multi‑agent orchestration). 
**Primary goals:** predictable green CI, stable pins, small PRs, hardened security, boring builds.

**Top endpoints:** `/healthz` (probe), `/docs` (Swagger), `/openapi.json`.

---

## 4) Kickoff Milestones (first 1–2 weeks)
- **M1 — Bootstrap sanity**
  - Add `scripts/bootstrap.sh` (prints Python, upgrades pip/wheel, installs from lock, runs ruff, smoke‑starts uvicorn, curls `/healthz`).
  - Add `.vscode/settings.json` (pin interpreter to `.venv/bin/python`).
- **M2 — CI guardrails**
  - Ensure Actions permissions, concurrency; lockfile freshness check as the gate; Trivy/Gitleaks non‑blocking.
- **M3 — Swagger/CSP**
  - Serve Swagger UI locally (no CDN), strict CSP headers; verify all docs/assets load under CSP.
- **M4 — GPU split (optional)**
  - Move Torch/Triton to `requirements-gpu.txt` (or `[gpu]` extra) if hashes break CI; base CI installs only the lockfile.
- **M5 — Paper cuts**
  - `.env.example`, predictable logs path, import path nits, shell helpers (`stop` alias, health check script).

---

## 5) Task Board (living list)
**Backlog**
- Preflight lockfile check (Linux-only compile) finalized.
- Harden Docker (non-root, read‑only FS, healthcheck) verified in CI.
- GHCR publish workflow main-only with proper permissions and concurrency.
- Add `/._well-known` probe endpoint returning 204 (CSP/strict environments).

**In Progress**
- (Add items as you start them.)

**Done**
- `.vscode/settings.json` tracked; ignore the rest of `.vscode/`.

---

## 6) Tiny PR Templates (copy‑paste)
**A) PR — Bootstrap sanity**
```
Title: chore(bootstrap): add bootstrap script + VS Code interpreter pin

- scripts/bootstrap.sh prints python, upgrades pip/wheel, installs from requirements.lock.txt, runs ruff, smoke‑starts uvicorn, curls /healthz
- add .vscode/settings.json to pin interpreter to .venv
- no app logic changes
```

**B) PR — CI guardrails**
```
Title: chore/ci: permissions, non-blocking scans, lockfile freshness gate

- set Actions permissions (contents read, packages write, id-token write, security-events write)
- make Trivy/Gitleaks informational on PRs; main builds/publishes
- add deterministic lockfile freshness check (Linux+3.11 only)
```

**C) PR — Swagger under strict CSP**
```
Title: feat(csp): local Swagger UI with strict CSP

- serve Swagger assets locally (no CDN)
- set CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- verify /docs renders fully under CSP
```

**D) PR — GPU split (optional)**
```
Title: chore(deps): move triton/torch to optional GPU extra to stabilize CI

- create requirements-gpu.txt (or `[gpu]` extra)
- CI installs only base lockfile
```

---

## 7) Scripts to Add
**scripts/bootstrap.sh** (sketch)
```bash
#!/usr/bin/env bash
set -euo pipefail
python -V
python -m pip install -U pip wheel
python -m pip install -r requirements.lock.txt --require-hashes || true
ruff format .
ruff check --fix . || true
# Smoke run
UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 8000 &"; eval "$UVICORN_CMD"; sleep 2
curl -fsS http://127.0.0.1:8000/healthz || true
pkill -f "uvicorn main:app" || true
```

---

## 8) Issue Template (for bugs)
```
Title: <clear, scoped bug>
Steps to Reproduce:
Expected:
Actual:
Logs/Screenshots:
Env (OS, Python, branch):
Acceptance Criteria:
- [ ] Repro added
- [ ] Fix implemented with test (if applicable)
- [ ] CI green
```

---

## 9) Contributor Quickstart (Mac)
1) Install Xcode CLT and Homebrew.
2) Create venv with **Python 3.11** and select it in VS Code.
3) `pip install -U pip wheel`
4) Install from lockfile (don’t generate on Mac).
5) Run `scripts/bootstrap.sh`.
6) `uvicorn main:app --reload`; open http://127.0.0.1:8000/docs

> If Torch wheels cause trouble on Mac, install CPU Torch locally (do **not** commit changes):
```bash
pip install torch==2.2.2 --extra-index-url https://download.pytorch.org/whl/cpu
```

---

## 10) Ready‑to‑Paste Project Summary (use for new chats)
```
RecoveryOS Project Context:
- FastAPI app; endpoints: /healthz, /docs, /openapi.json
- Non-negotiables: Python 3.11 everywhere; fixed Torch pin; ruff-only; lockfile on Linux+3.11; strict CSP + local Swagger
- CI: PR scans informational; main builds/publishes; Actions perms set; lockfile freshness gate
- Branch hygiene: small PRs; names like chore/ci-stability, ci/ghcr-build-push, feat/csp-env-middleware, ops/ruff-py311-bootstrap
- Local dev: .vscode/settings.json pins interpreter; avoid Mac lockfile regen
```

---

## 11) Links (fill these in)
- GitHub repo: <link>
- GH Actions: <link>
- GHCR package: <link>
- Project board (if used): <link>
- Notion/Docs: <link>

---

## 12) Notes
- Keep this doc updated as a single source of truth.
- Use the **Task Board** above to track work across chats.
