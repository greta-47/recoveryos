CI guide

Overview
- CI runs on GitHub Actions via .github/workflows/preflight.yml.
- Python 3.12 is used in CI. The Dockerfile currently uses Python 3.11.9; this difference is intentional for now.

Local checks
- Use the same tools as CI:
  - Ruff for lint
  - Black for formatting
  - Isort for import sorting
  - Python bytecode compile for syntax check

Install tooling
- Optional (recommended): install pre-commit to run checks on commit
  - pip install pre-commit
  - pre-commit install

Run checks manually
- Ruff:
  - ruff check .
- Black:
  - black --check .
  - To autoformat: black .
- Isort:
  - isort --check-only .
  - To apply: isort .
- Syntax:
  - python -m py_compile $(find . -name "*.py" | grep -v venv)

Docker build check
- docker build .

Notes
- Tool configuration is in pyproject.toml.
- Keep diffs small; only fix issues needed for CI to pass.
