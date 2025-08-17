#!/usr/bin/env bash

URL=${1:-https://localhost:8000/health}

echo "🔍 Checking headers for $URL"
curl -skI "$URL" | tee /tmp/headers.out

echo
echo "🔒 Expected headers:"
grep -i "strict-transport-security" /tmp/headers.out || echo "❌ Missing HSTS"
grep -i "x-frame-options" /tmp/headers.out || echo "❌ Missing X-Frame-Options"
grep -i "x-content-type-options" /tmp/headers.out || echo "❌ Missing X-Content-Type-Options"
grep -i "referrer-policy" /tmp/headers.out || echo "❌ Missing Referrer-Policy"
grep -i "content-security-policy" /tmp/headers.out || grep -i "content-security-policy-report-only" /tmp/headers.out || echo "❌ Missing CSP"

echo
echo "✅ Smoke check complete"
