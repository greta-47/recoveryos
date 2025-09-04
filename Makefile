# RecoveryOS Makefile — Python 3.11 + deterministic lockfile + ruff-only
# Usage: `make help`

SHELL := /bin/bash
PY := python
PIP := $(PY) -m pip

.DEFAULT_GOAL := help

## help: Show available commands
help:
	@awk 'BEGIN {FS":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## lock: Regenerate requirements.lock.txt on Linux (pip==24.2.1 + pip-tools==7.4.1) with hashes
lock:
	@docker run --rm -v "$$PWD":/app -w /app python:3.11-slim bash -lc "\
		python -m pip install 'pip==24.2.1' 'pip-tools==7.4.1' && \
		pip-compile --generate-hashes -o requirements.lock.txt requirements.txt \
	"

## lint: Run Ruff format check + lint (non-fixing)
lint:
	@$(PIP) install -U ruff >/dev/null
	@ruff format --check .
	@ruff check .

## fix: Run Ruff formatter and autofix
fix:
	@$(PIP) install -U ruff >/dev/null
	@ruff format .
	@ruff check --fix .

## smoke: Run the uvicorn smoke test (GET /healthz) via scripts/smoke.sh
smoke:
	@chmod +x scripts/smoke.sh || true
	@bash scripts/smoke.sh

## ci-preflight: Locally simulate the lockfile preflight diff (Linux-in-docker)
ci-preflight:
	@docker run --rm -v "$$PWD":/app -w /app python:3.11-slim bash -lc '\
		python -m pip install "pip==24.2.1" "pip-tools==7.4.1" >/dev/null && \
		pip-compile --quiet --generate-hashes -o /tmp/requirements.lock.txt requirements.txt && \
		awk '!/^[[:space:]]*#/' requirements.lock.txt > /tmp/current.txt; \
		awk '!/^[[:space:]]*#/' /tmp/requirements.lock.txt > /tmp/new.txt; \
		if ! diff -u /tmp/current.txt /tmp/new.txt; then \
			echo ""; \
			echo "::error::Lockfile is stale relative to requirements.txt"; \
			exit 1; \
		else \
			echo "Lockfile is fresh."; \
		fi'

.PHONY: help lock lint fix smoke ci-preflight
