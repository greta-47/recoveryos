# Canary Deployment Runbook

## Overview
This runbook provides step-by-step instructions for deploying RecoveryOS elite AI endpoints using a canary deployment strategy with automatic rollback capabilities.

## Prerequisites
- Access to production Kubernetes cluster
- Helm charts deployed
- Monitoring dashboards configured
- Feature flag system operational

## Canary Deployment Process

### Phase 1: Pre-Deployment Checks (5 minutes)

1. **Verify staging environment**
   ```bash
   # Check all endpoints are healthy
   curl -s http://staging.recoveryos.com/elite/metrics | jq '.avg_success_rate'
   
   # Verify feature flags
   curl -s http://staging.recoveryos.com/elite/system-status | jq '.features'
   ```

2. **Check production baseline metrics**
   ```bash
   # Record baseline metrics
   kubectl get pods -n recoveryos
   kubectl top pods -n recoveryos
   ```

3. **Enable canary feature flag**
   ```bash
   # Update feature flag to enable canary
   curl -X POST http://admin.recoveryos.com/feature-flags/release_20250814 \
     -H "Content-Type: application/json" \
     -d '{"enabled": true, "rollout_percentage": 5, "environment": "production"}'
   ```

### Phase 2: 5% Traffic Canary (30 minutes)

1. **Deploy canary version**
   ```bash
   # Deploy new version with canary label
   helm upgrade recoveryos-canary ./helm/recoveryos \
     --set image.tag=v1.0.0-elite \
     --set replicaCount=1 \
     --set canary.enabled=true \
     --set canary.weight=5 \
     --namespace recoveryos
   ```

2. **Monitor SLOs for 30 minutes**
   - **P95 latency**: Must stay < 600ms (SLA + 20%)
   - **5xx error rate**: Must stay < 1%
   - **Error budget burn**: Must stay < 2x baseline

3. **Automated monitoring commands**
   ```bash
   # Monitor latency
   watch -n 30 'curl -s http://monitoring.recoveryos.com/metrics | grep p95_latency'
   
   # Monitor error rate
   watch -n 30 'curl -s http://monitoring.recoveryos.com/metrics | grep error_rate'
   ```

### Phase 3: 10% Traffic (30 minutes)

1. **Increase traffic if Phase 1 successful**
   ```bash
   # Update canary weight
   helm upgrade recoveryos-canary ./helm/recoveryos \
     --set canary.weight=10 \
     --reuse-values
   
   # Update feature flag
   curl -X POST http://admin.recoveryos.com/feature-flags/release_20250814 \
     -H "Content-Type: application/json" \
     -d '{"rollout_percentage": 10}'
   ```

2. **Continue monitoring with same SLO thresholds**

### Phase 4: Full Rollout (25%, 50%, 100%)

1. **25% Traffic (30 minutes)**
   ```bash
   helm upgrade recoveryos-canary ./helm/recoveryos --set canary.weight=25 --reuse-values
   ```

2. **50% Traffic (30 minutes)**
   ```bash
   helm upgrade recoveryos-canary ./helm/recoveryos --set canary.weight=50 --reuse-values
   ```

3. **100% Traffic (Full deployment)**
   ```bash
   # Promote canary to main deployment
   helm upgrade recoveryos ./helm/recoveryos \
     --set image.tag=v1.0.0-elite \
     --set canary.enabled=false
   
   # Remove canary deployment
   helm uninstall recoveryos-canary -n recoveryos
   ```

## Automatic Rollback Triggers

### SLO Breach Detection
The system automatically monitors:
- **P95 latency > 600ms** for 5 consecutive minutes
- **5xx error rate > 1%** over 5-minute window
- **Error budget burn > 2x baseline** for 10 minutes

### Rollback Commands

1. **Immediate rollback (emergency)**
   ```bash
   # Disable feature flag immediately
   curl -X POST http://admin.recoveryos.com/feature-flags/release_20250814 \
     -H "Content-Type: application/json" \
     -d '{"enabled": false, "rollout_percentage": 0}'
   
   # Rollback Helm deployment
   helm rollback recoveryos -n recoveryos
   
   # Remove canary
   helm uninstall recoveryos-canary -n recoveryos
   ```

2. **Gradual rollback**
   ```bash
   # Reduce traffic gradually
   helm upgrade recoveryos-canary ./helm/recoveryos --set canary.weight=0 --reuse-values
   
   # Wait 5 minutes, then remove
   helm uninstall recoveryos-canary -n recoveryos
   ```

## Monitoring Commands

### Real-time Monitoring
```bash
# Dashboard URLs
echo "Grafana: http://grafana.recoveryos.com/d/elite-endpoints"
echo "Prometheus: http://prometheus.recoveryos.com/graph"
echo "Jaeger: http://jaeger.recoveryos.com/search"

# CLI monitoring
kubectl logs -f deployment/recoveryos-canary -n recoveryos | grep ERROR
kubectl top pods -n recoveryos --sort-by=cpu
```

### Key Metrics to Watch
```bash
# P95 latency per endpoint
curl -s http://prometheus.recoveryos.com/api/v1/query?query='histogram_quantile(0.95, recoveryos_request_duration_seconds_bucket)'

# Error rate
curl -s http://prometheus.recoveryos.com/api/v1/query?query='rate(recoveryos_errors_total[5m])'

# Request rate
curl -s http://prometheus.recoveryos.com/api/v1/query?query='rate(recoveryos_requests_total[5m])'
```

## Rollback Decision Matrix

| Metric | Threshold | Action | Urgency |
|--------|-----------|--------|---------|
| P95 latency > 600ms | 5 min | Gradual rollback | Medium |
| P95 latency > 1000ms | 2 min | Immediate rollback | High |
| 5xx rate > 1% | 5 min | Gradual rollback | Medium |
| 5xx rate > 5% | 1 min | Immediate rollback | Critical |
| Error budget burn > 2x | 10 min | Gradual rollback | Medium |
| Error budget burn > 5x | 2 min | Immediate rollback | High |

## Communication Plan

### Slack Notifications
```bash
# Success notification
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{"text": "✅ Canary deployment Phase 1 (5%) successful. P95: 450ms, Error rate: 0.1%"}'

# Rollback notification  
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{"text": "🚨 ROLLBACK INITIATED: P95 latency exceeded 600ms threshold"}'
```

### Stakeholder Updates
- **Engineering Team**: Real-time Slack updates
- **Product Team**: Email summary after each phase
- **Clinical Team**: Notification only if rollback occurs

## Post-Deployment

### Success Criteria
- [ ] All SLOs maintained throughout deployment
- [ ] No customer-reported issues
- [ ] Monitoring dashboards show healthy metrics
- [ ] Feature flag at 100% rollout

### Cleanup Tasks
```bash
# Remove canary resources
kubectl delete configmap recoveryos-canary-config -n recoveryos
kubectl delete service recoveryos-canary -n recoveryos

# Update documentation
git add runbooks/canary.md
git commit -m "Update canary deployment runbook with latest deployment"
```

## Troubleshooting

### Common Issues

1. **High latency during deployment**
   - Check resource limits: `kubectl describe pods -n recoveryos`
   - Verify database connections: `kubectl logs deployment/recoveryos -n recoveryos | grep database`

2. **Increased error rate**
   - Check application logs: `kubectl logs -f deployment/recoveryos-canary -n recoveryos`
   - Verify external dependencies: `curl -s http://api.openai.com/health`

3. **Feature flag not taking effect**
   - Verify flag configuration: `curl -s http://admin.recoveryos.com/feature-flags/release_20250814`
   - Check application restart: `kubectl rollout restart deployment/recoveryos -n recoveryos`

### Emergency Contacts
- **On-call Engineer**: +1-555-0123
- **DevOps Lead**: +1-555-0124  
- **Product Manager**: +1-555-0125

---
*Last updated: August 14, 2025*
*Next review: August 21, 2025*
