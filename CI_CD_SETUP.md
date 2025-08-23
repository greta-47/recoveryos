# CI/CD Setup and Branch Protection Rules

## Required GitHub Repository Settings

### Branch Protection Rules for `main` branch:

1. **Require status checks to pass before merging**
   - Enable: "Require status checks to pass before merging"
   - Required status checks:
     - `test / Unit & E2E Tests`
     - `security / Security Scans`
     - `lint / Code Quality & Formatting`
     - `build / Build & Container Scan`

2. **Require pull request reviews before merging**
   - Enable: "Require pull request reviews before merging"
   - Required approving reviews: 1
   - Enable: "Dismiss stale pull request approvals when new commits are pushed"

3. **Require branches to be up to date before merging**
   - Enable: "Require branches to be up to date before merging"

4. **Restrict pushes that create files**
   - Enable: "Restrict pushes that create files"
   - Allowed file patterns: `*.md`, `*.json`, `*.yml`, `*.yaml`

### Required Secrets Configuration:

- `OPENAI_API_KEY`: For AI functionality testing
- `CODECOV_TOKEN`: For coverage reporting
- `GITLEAKS_LICENSE`: For secret scanning (optional)

### Merge Settings:

- Enable: "Allow squash merging"
- Disable: "Allow merge commits"
- Disable: "Allow rebase merging"
- Enable: "Automatically delete head branches"

## CI/CD Pipeline Overview

### Test Pipeline (`test`)
- **Purpose**: Unit and E2E testing with coverage requirements
- **Coverage Threshold**: 80% for changed code
- **Blocking**: Yes - PRs cannot merge if tests fail or coverage < 80%

### Security Pipeline (`security`)
- **Purpose**: Dependency and code security scanning
- **Tools**: pip-audit, safety, bandit, gitleaks
- **Blocking**: Yes - PRs cannot merge on HIGH severity vulnerabilities

### Lint Pipeline (`lint`)
- **Purpose**: Code quality and formatting
- **Tools**: black, ruff, mypy
- **Blocking**: Yes - PRs cannot merge on lint failures

### Build Pipeline (`build`)
- **Purpose**: Docker image build and container scanning
- **Tools**: Docker, Trivy
- **Blocking**: Yes - PRs cannot merge on build failures

## Monitoring and Observability

### Metrics Collection
- **Prometheus**: `/metrics` endpoint for scraping
- **Labels**: endpoint, version, env, status
- **Key Metrics**: request_count, latency_histogram, error_rate, active_requests

### Distributed Tracing
- **Correlation IDs**: Automatic generation and propagation
- **Span Tracking**: Handler → Model Call → Datastore
- **Structured Logging**: JSON format with PII redaction

### Dashboard Configuration
- **Grafana**: See `monitoring/grafana-dashboard.json`
- **Prometheus**: See `monitoring/prometheus-config.yml`

## Canary Deployment Process

### Feature Flag: `release_20250814`
- **Staging**: 100% enabled
- **Production**: 0% initially, gradual rollout to 5-10%

### Auto-Rollback Triggers
- P95 latency > 600ms for 5+ minutes
- Error rate > 1% for 5+ minutes
- Error budget burn > 2x baseline

### Rollback Procedure
1. Set feature flag to 0% via `feature_flags.py`
2. Monitor metrics for 10 minutes
3. If issues persist, revert Docker image
4. Escalate to on-call engineer

## Load Testing Requirements

### Target Endpoints
- Continual Learning: `/elite/continual-learning/train`
- Federated Learning: `/elite/federated-learning/train`
- Edge AI: `/elite/edge-ai/deploy`

### Performance SLAs
- **P95 Latency**: < 500ms
- **Error Rate**: < 1%
- **Throughput**: 10 RPS sustained for 20-30 minutes

### Test Execution
```bash
# Install k6 via Docker
docker run --rm -v $(pwd):/app -w /app grafana/k6 run load_testing/k6_soak_test.js

# Generate performance reports
k6 run --out json=results.json load_testing/k6_soak_test.js
```

## Verification Commands

```bash
# Test CI/CD pipeline
git push origin feature-branch  # Should trigger all checks

# Test security scanning
pip-audit --desc --format=json --output=audit.json
bandit -r . -f json -o bandit.json

# Test coverage
pytest test_elite_endpoints.py --cov=main --cov-fail-under=80

# Test PII redaction
python -c "from observability_enhanced import PIIRedactor; print(PIIRedactor.redact_pii('Contact john.doe@example.com or 555-123-4567'))"

# Test metrics endpoint
curl http://localhost:8001/metrics

# Test feature flags
python -c "from feature_flags import feature_flags; print(feature_flags.is_enabled('release_20250814'))"
```

## Troubleshooting

### Common Issues

1. **Coverage Below 80%**
   - Add tests for new functions/classes
   - Exclude test files from coverage: `--cov-config=.coveragerc`

2. **Security Scan Failures**
   - Update vulnerable dependencies in `requirements.txt`
   - Add exceptions for false positives in `.bandit`

3. **Lint Failures**
   - Run `black .` to auto-format code
   - Fix ruff issues: `ruff check . --fix`

4. **Load Test Failures**
   - Check server capacity and scaling
   - Verify endpoint functionality before load testing
   - Monitor resource usage during tests

### Emergency Procedures

1. **Production Incident**
   - Immediately set `release_20250814` to 0%
   - Monitor error rates and latency
   - Escalate to on-call if issues persist

2. **CI/CD Pipeline Down**
   - Check GitHub Actions status
   - Verify secrets and permissions
   - Use manual deployment process if critical

3. **Monitoring Outage**
   - Check Prometheus/Grafana connectivity
   - Verify metrics endpoint accessibility
   - Use application logs for debugging
