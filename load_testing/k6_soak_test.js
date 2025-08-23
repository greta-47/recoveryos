import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');

export const options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up
    { duration: '25m', target: 10 }, // Extended soak test
    { duration: '3m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    errors: ['rate<0.01'], // Error rate under 1%
    'http_req_duration{endpoint:continual_learning}': ['p(95)<600'],
    'http_req_duration{endpoint:federated_learning}': ['p(95)<800'],
    'http_req_duration{endpoint:edge_ai}': ['p(95)<400'],
  },
};

const BASE_URL = 'http://localhost:8001';

const testData = {
  continual_learning: {
    task_data: { stress_patterns: [0.8, 0.6, 0.9] },
    task_id: 'stress_prediction_load_test'
  },
  federated_learning: {
    client_weights: [0.1, 0.2, 0.3, 0.4, 0.5],
    client_id: `load_test_client_${__VU}_${__ITER}`
  },
  edge_ai: {
    model_type: 'emotion_classifier'
  }
};

export default function () {
  const endpoints = [
    {
      name: 'continual_learning',
      url: `${BASE_URL}/elite/continual-learning/train`,
      payload: testData.continual_learning
    },
    {
      name: 'federated_learning', 
      url: `${BASE_URL}/elite/federated-learning/train`,
      payload: testData.federated_learning
    },
    {
      name: 'edge_ai',
      url: `${BASE_URL}/elite/edge-ai/deploy`,
      payload: testData.edge_ai
    }
  ];

  endpoints.forEach(endpoint => {
    const response = http.post(endpoint.url, JSON.stringify(endpoint.payload), {
      headers: {
        'Content-Type': 'application/json',
      },
      tags: { endpoint: endpoint.name },
    });

    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response has data': (r) => r.json() !== null,
      'response time < 1000ms': (r) => r.timings.duration < 1000,
    });

    errorRate.add(!success);
    responseTime.add(response.timings.duration, { endpoint: endpoint.name });

    if (!success) {
      console.error(`${endpoint.name} failed:`, response.status, response.body);
    }
  });

  sleep(1); // 1 second between iterations
}

export function handleSummary(data) {
  return {
    'load_test_results.json': JSON.stringify(data, null, 2),
    'load_test_summary.html': htmlReport(data),
  };
}

function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>RecoveryOS Elite Endpoints Load Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
        .pass { background-color: #d4edda; }
        .fail { background-color: #f8d7da; }
    </style>
</head>
<body>
    <h1>Load Test Results</h1>
    <h2>Summary</h2>
    <div class="metric ${data.metrics.http_req_duration.values.p95 < 500 ? 'pass' : 'fail'}">
        <strong>P95 Response Time:</strong> ${data.metrics.http_req_duration.values.p95.toFixed(2)}ms
        (Threshold: <500ms)
    </div>
    <div class="metric ${data.metrics.errors.values.rate < 0.01 ? 'pass' : 'fail'}">
        <strong>Error Rate:</strong> ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
        (Threshold: <1%)
    </div>
    <div class="metric">
        <strong>Total Requests:</strong> ${data.metrics.http_reqs.values.count}
    </div>
    <div class="metric">
        <strong>Average Response Time:</strong> ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
    </div>
</body>
</html>
  `;
}
