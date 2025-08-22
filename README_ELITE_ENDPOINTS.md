# Elite AI Endpoints Documentation

This document provides comprehensive testing examples for the Elite AI endpoints in RecoveryOS.

## Overview

The Elite AI endpoints provide advanced functionality including:
- Health monitoring and status checks
- Performance metrics and observability
- Federated learning client management
- Enhanced privacy and security features

## Authentication

All Elite endpoints require API key authentication via the `X-API-Key` header:

```bash
export API_KEY="your-api-key-here"
```

## Endpoints

### 1. Elite Health Check

**Endpoint:** `GET /elite/health`

**Description:** Returns the health status of the Elite AI pipeline and its components.

**Example:**
```bash
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/elite/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "Elite AI Pipeline",
  "timestamp": "2025-08-22T22:30:00Z",
  "components": {
    "federated_learning": "active",
    "differential_privacy": "enabled",
    "neuromorphic_processing": "ready"
  }
}
```

### 2. Elite Metrics

**Endpoint:** `GET /elite/metrics`

**Description:** Returns comprehensive observability metrics for performance monitoring.

**Example:**
```bash
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/elite/metrics
```

**Response:**
```json
{
  "timestamp": "2025-08-22T22:30:00Z",
  "performance": {
    "avg_response_time_ms": 245,
    "requests_per_second": 12.5,
    "error_rate": 0.02
  },
  "federated_learning": {
    "active_clients": 3,
    "model_version": "v2.1.0",
    "last_aggregation": "2025-08-22T22:15:00Z"
  },
  "privacy": {
    "pii_redaction_rate": 0.98,
    "differential_privacy_epsilon": 1.0
  }
}
```

### 3. Federated Client Registration

**Endpoint:** `POST /elite/federated/register`

**Description:** Register a new federated learning client with the system.

**Example:**
```bash
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "client_id": "hospital_001",
       "client_type": "hospital",
       "capabilities": ["imaging", "nlp", "prediction"],
       "privacy_level": "high"
     }' \
     http://localhost:8000/elite/federated/register
```

**Request Body:**
```json
{
  "client_id": "hospital_001",
  "client_type": "hospital",
  "capabilities": ["imaging", "nlp", "prediction"],
  "privacy_level": "high"
}
```

**Valid client_type values:** `hospital`, `clinic`, `research`
**Valid privacy_level values:** `basic`, `standard`, `high`

**Response:**
```json
{
  "status": "registered",
  "client_id": "hospital_001",
  "assigned_model_version": "v2.1.0",
  "next_sync": "2025-08-22T23:00:00Z",
  "privacy_config": {
    "epsilon": 0.5,
    "delta": 1e-5
  },
  "request_id": "uuid-here",
  "timestamp": "2025-08-22T22:30:00Z"
}
```

### 4. List Federated Clients

**Endpoint:** `GET /elite/federated/clients`

**Description:** List all registered federated learning clients and their status.

**Example:**
```bash
curl -H "X-API-Key: $API_KEY" \
     http://localhost:8000/elite/federated/clients
```

**Response:**
```json
{
  "clients": [
    {
      "client_id": "hospital_001",
      "client_type": "hospital",
      "status": "active",
      "last_sync": "2025-08-22T22:15:00Z",
      "model_version": "v2.1.0"
    },
    {
      "client_id": "clinic_002",
      "client_type": "clinic", 
      "status": "active",
      "last_sync": "2025-08-22T22:10:00Z",
      "model_version": "v2.1.0"
    }
  ],
  "total_clients": 2,
  "timestamp": "2025-08-22T22:30:00Z"
}
```

## Testing Scenarios

### Manual Testing with curl

1. **Basic Health Check:**
```bash
curl -v -H "X-API-Key: $API_KEY" http://localhost:8000/elite/health
```

2. **Monitor Metrics During Load:**
```bash
# Run this while generating load to see metrics change
watch -n 5 "curl -s -H 'X-API-Key: $API_KEY' http://localhost:8000/elite/metrics | jq '.performance'"
```

3. **Test Client Registration Edge Cases:**
```bash
# Invalid client type
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"client_id": "test", "client_type": "invalid"}' \
     http://localhost:8000/elite/federated/register

# Missing required fields
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"client_type": "hospital"}' \
     http://localhost:8000/elite/federated/register
```

4. **Authentication Testing:**
```bash
# Should return 401
curl -v http://localhost:8000/elite/health

# Should return 401
curl -v -H "X-API-Key: wrong-key" http://localhost:8000/elite/health
```

### Load Testing

Use the provided `test_elite_endpoints.py` script for comprehensive testing:

```bash
# Install dependencies
pip install pytest requests

# Set environment variables
export API_KEY="your-api-key"
export TEST_BASE_URL="http://localhost:8000"

# Run all tests
python test_elite_endpoints.py

# Or run with pytest
pytest test_elite_endpoints.py -v
```

### Performance Monitoring

Monitor the `/elite/metrics` endpoint during testing to validate:

- Response times remain under acceptable thresholds
- Error rates stay low
- PII redaction rates are high (>95%)
- Federated learning clients stay synchronized

### PII Redaction Testing

Test PII redaction with the agents endpoint:

```bash
# This should trigger PII redaction
curl -X POST \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "Patient John Doe DOB: 1985-03-15 has concerning symptoms"
     }' \
     http://localhost:8000/agents/run
```

Expected behavior: Either rejection (400 error) or redacted output containing `[REDACTED]`.

## Integration with CI/CD

Add these tests to your CI pipeline:

```yaml
- name: Test Elite Endpoints
  run: |
    export API_KEY="${{ secrets.API_KEY }}"
    export TEST_BASE_URL="http://localhost:8000"
    python test_elite_endpoints.py
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized:** Check that `API_KEY` environment variable is set correctly
2. **422 Validation Error:** Verify request body matches the expected schema
3. **503 Service Unavailable:** Ensure all dependencies are installed and services are running

### Debug Mode

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

This will provide detailed request/response logging for troubleshooting.
