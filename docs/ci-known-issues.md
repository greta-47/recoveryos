# CI Known Issues and Standard Fixes

## Lockfile Regeneration on Linux

**Issue**: Hash mismatches in requirements.lock.txt causing `--require-hashes` failures

**Fix**: Regenerate on Linux using Docker:
```bash
docker run --rm -v "$PWD":/w -w /w python:3.11-slim bash -lc '
  set -euo pipefail
  python -m pip install 'pip==24.2.1' 'pip-tools==7.4.1'
  if [ -f requirements.base.in ]; then
    pip-compile --quiet --generate-hashes -o requirements.lock.txt requirements.base.in
  else
    pip-compile --quiet --generate-hashes -o requirements.lock.txt requirements.txt
  fi
'
```

## Workflow Permission Issues

**Issue**: Gitleaks permission errors with "Resource not accessible by integration"

**Fix**: Ensure workflows have proper permissions block:
```yaml
permissions:
  contents: read
  pull-requests: read
  security-events: write
```

## Trivy SARIF Upload Issues

**Issue**: SARIF upload fails when Trivy doesn't generate expected file

**Fix**: Add existence check before upload:
```yaml
- id: sarif
  name: Check SARIF exists
  run: |
    if [ -f trivy-results.sarif ]; then
      echo "exists=true" >> "$GITHUB_OUTPUT"
    fi

- name: Upload SARIF
  if: ${{ steps.sarif.outputs.exists == 'true' }}
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: trivy-results.sarif
```

## GitHub Actions Expression Syntax

**Issue**: Functions like `secrets.OPENAI_API_KEY` must be wrapped in `${{ }}`

**Fix**: Use `if: ${{ secrets.OPENAI_API_KEY != '' }}` not `if: secrets.OPENAI_API_KEY != ''`

## GHCR Build Workflow Configuration

**Required settings** for main-only publishing with proper permissions:
```yaml
on:
  push:
    branches: ["main"]
permissions:
  contents: read
  packages: write
  security-events: write
  id-token: write
concurrency:
  group: ghcr-${{ github.ref }}
  cancel-in-progress: true
```

## GPU Dependencies and Hash Issues

**Strategy**: If Triton breaks hash resolution, split dependencies:
- Create requirements-gpu.txt for Torch/Triton pins
- Keep requirements.txt/lockfile CPU-safe for CI
- Configure Docker/CI to install base lockfile only

**Implementation**:
```bash
# Split dependencies
echo "torch>=2.0.0" > requirements-gpu.txt
echo "triton>=2.0.0" >> requirements-gpu.txt

# Generate separate lockfiles
pip-compile --generate-hashes -o requirements.lock.txt requirements.txt
pip-compile --generate-hashes -o requirements-gpu.lock.txt requirements-gpu.txt

# CI installs base only
pip install -r requirements.lock.txt --require-hashes

# GPU users install both
pip install -r requirements.lock.txt --require-hashes
pip install -r requirements-gpu.lock.txt --require-hashes
```

## Trivy Disk Space Mitigation

**Issue**: Trivy fails with "no space left on device" during vulnerability scanning

**Fix**: Use vuln-only scanning and non-blocking mode:
```yaml
- name: Trivy image scan (non-blocking)
  continue-on-error: true
  uses: aquasecurity/trivy-action@v0.28.0
  with:
    scanners: vuln
    format: sarif
    output: trivy-results.sarif
```

## Bootstrap and Smoke Scripts

**Bootstrap script** (`scripts/bootstrap_devin.sh`):
- Installs dependencies from requirements.txt
- Runs non-blocking ruff format/check
- Starts uvicorn server on port 8000

**Smoke script** (`scripts/smoke.sh`):
- Tests health endpoint at `/healthz`
- Accepts custom URL as first argument
- Returns 0 for success, 1 for failure

**Usage**:
```bash
# Start application
bash scripts/bootstrap_devin.sh

# Test health (in another terminal)
bash scripts/smoke.sh
bash scripts/smoke.sh http://localhost:8000/healthz
```
