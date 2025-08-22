CSP via environment

Overview
- An ASGI middleware sets the Content Security Policy header based on environment variables.
- Inline scripts and eval are blocked by default.
- You can allow a web app origin and a comma-separated CDN list via env.

Environment variables
- CSP_APP_ORIGIN: single origin allowed in addition to 'self' (default: https://app.my-domain.com)
- CSP_CDN_LIST: comma-separated list of allowed CDN origins (e.g., https://cdn.example.com, https://static.example.org)
- CSP_REPORT_ONLY: if true, sends Content-Security-Policy-Report-Only instead of enforcing CSP

Defaults
- default-src/script-src/style-src/font-src/connect-src/img-src include: 'self', CSP_APP_ORIGIN, and any CDNs
- object-src 'none'
- base-uri 'self'
- frame-ancestors 'none'

Copy-ready env examples

Dev (.env)
CSP_APP_ORIGIN=http://localhost:3000
CSP_CDN_LIST=https://cdn.jsdelivr.net, https://unpkg.com
CSP_REPORT_ONLY=true

Prod (.env.prod)
CSP_APP_ORIGIN=https://app.my-domain.com
CSP_CDN_LIST=https://cdn.jsdelivr.net, https://unpkg.com
CSP_REPORT_ONLY=false

Verification
- CI runs a minimal integration test to assert CSP headers.
- You can also run locally:
  - export the envs above
  - python -m uvicorn main:app
  - curl -sI http://127.0.0.1:8000/healthz | grep -i content-security-policy

Notes
- Additional security headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) can be set at your gateway/CDN or added in a future middleware if desired.
