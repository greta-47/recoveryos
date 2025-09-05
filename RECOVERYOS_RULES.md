# RecoveryOS — Pinned Rules

**Repo:** `greta-47/recoveryos` (FastAPI app)  
- Health: `/healthz`  
- Docs: `/docs`  
- OpenAPI: `/openapi.json`  

---

## 🎯 Primary Goals
- Keep **CI green and predictable**  
- Keep **Python/Torch pins steady**  
- Land **small, focused PRs**  

---

## 🔒 Guardrails
- **Python 3.11 everywhere**  
  - Local venv, Dockerfile, GitHub Actions  
- **Torch pin fixed**  
  - If CI breaks due to Triton/hashes → split GPU deps (`requirements-gpu.txt` or `[gpu]` extra)  
- **Ruff-only lint & format**  
  ```bash
  ruff format .
  ruff check --fix .

# In VS Code terminal, make sure you’re in the repo root
cd ~/path/to/recoveryos

git checkout -b chore/add-project-docs

# Move your existing desktop files into the repo
mv ~/Desktop/RECOVERYOS_PROJECT_HOME.md .
mv ~/Desktop/RECOVERYOS_PROJECT_KICKOFF.md .

# Create the rules file in one shot
cat > RECOVERYOS_RULES.md <<'EOF'
# RecoveryOS — Pinned Rules

**Repo:** `greta-47/recoveryos` (FastAPI app)  
- Health: `/healthz`  
- Docs: `/docs`  
- OpenAPI: `/openapi.json`  

---

## 🎯 Primary Goals
- Keep **CI green and predictable**  
- Keep **Python/Torch pins steady**  
- Land **small, focused PRs**  

---

## 🔒 Guardrails
- **Python 3.11 everywhere**  
  - Local venv, Dockerfile, GitHub Actions  
- **Torch pin fixed**  
  - If CI breaks due to Triton/hashes → split GPU deps (`requirements-gpu.txt` or `[gpu]` extra)  
- **Ruff-only lint & format**  
  ```bash
  ruff format .
  ruff check --fix .

# In VS Code terminal, make sure you’re in the repo root
cd ~/path/to/recoveryos

git checkout -b chore/add-project-docs

# Move your existing desktop files into the repo
mv ~/Desktop/RECOVERYOS_PROJECT_HOME.md .
mv ~/Desktop/RECOVERYOS_PROJECT_KICKOFF.md .

# Create the rules file in one shot
cat > RECOVERYOS_RULES.md <<'EOF'
# RecoveryOS — Pinned Rules

**Repo:** `greta-47/recoveryos` (FastAPI app)  
- Health: `/healthz`  
- Docs: `/docs`  
- OpenAPI: `/openapi.json`  

---

## 🎯 Primary Goals
- Keep **CI green and predictable**  
- Keep **Python/Torch pins steady**  
- Land **small, focused PRs**  

---

## 🔒 Guardrails
- **Python 3.11 everywhere**  
  - Local venv, Dockerfile, GitHub Actions  
- **Torch pin fixed**  
  - If CI breaks due to Triton/hashes → split GPU deps (`requirements-gpu.txt` or `[gpu]` extra)  
- **Ruff-only lint & format**  
  ```bash
  ruff format .
  ruff check --fix .

