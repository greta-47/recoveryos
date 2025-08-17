import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 1,
  iterations: 1,
};

export default function () {
  let url = __ENV.URL || 'https://localhost:8000/health';
  let res = http.get(url, { insecureSkipTLSVerify: true });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has HSTS': (r) => r.headers['Strict-Transport-Security'] !== undefined,
    'has XFO': (r) => r.headers['X-Frame-Options'] === 'DENY',
    'has XCTO': (r) => r.headers['X-Content-Type-Options'] === 'nosniff',
    'has Referrer-Policy': (r) => r.headers['Referrer-Policy'] === 'no-referrer',
    'has CSP': (r) =>
      r.headers['Content-Security-Policy'] !== undefined ||
      r.headers['Content-Security-Policy-Report-Only'] !== undefined,
  });
}
