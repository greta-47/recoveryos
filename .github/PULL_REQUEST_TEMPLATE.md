## Description

Brief description of changes made.

## Acceptance Checklist

- [ ] **Ruff formatting**: `make fix` passes without errors
- [ ] **Lockfile policy**: If requirements.txt changed, regenerated requirements.lock.txt using `make lock`
- [ ] **Branch naming**: Follows convention (chore/, feat/, ci/, ops/, etc.)
- [ ] **No build artifacts**: No __pycache__/, *.pyc, logs, coverage files committed
- [ ] **No environment files**: No .env* files committed (use .env.example for templates)
- [ ] **Single purpose**: PR scope matches title, no unrelated changes
- [ ] **CI passing**: All required checks green (lockfile preflight is required)

## Testing

- [ ] Tested locally using `make smoke` or equivalent
- [ ] Verified changes don't break existing functionality

## Security

- [ ] No secrets or keys committed to repository
- [ ] PHI handling follows established patterns (if applicable)
