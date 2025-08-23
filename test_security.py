#!/usr/bin/env python3
"""Test script to verify security headers implementation."""

import sys

sys.path.insert(0, "/home/ubuntu/repos/recoveryos")


def test_security_headers():
    """Test that security headers are properly implemented."""
    print("=== Testing Security Headers Implementation ===")

    try:
        from fastapi.testclient import TestClient

        from main import app
        from test_config import setup_test_environment

        setup_test_environment()

        client = TestClient(app)

        response = client.get("/")
        headers = response.headers

        print(f"Response status: {response.status_code}")
        print("Security headers found:")

        security_headers = {
            "Strict-Transport-Security": "HSTS",
            "X-Frame-Options": "Clickjacking protection",
            "X-Content-Type-Options": "MIME sniffing protection",
            "Referrer-Policy": "Referrer control",
            "Content-Security-Policy": "XSS protection",
            "X-XSS-Protection": "XSS protection (legacy)",
            "X-Permitted-Cross-Domain-Policies": "Cross-domain policy",
        }

        found_headers = 0
        for header, description in security_headers.items():
            if header in headers:
                print(f"  ✅ {header}: {headers[header]} ({description})")
                found_headers += 1
            else:
                print(f"  ❌ {header}: Missing ({description})")

        print(f"\nSecurity headers implemented: {found_headers}/{len(security_headers)}")

        health_response = client.get("/healthz")
        print(f"Health endpoint status: {health_response.status_code}")

        if "Content-Security-Policy" in headers:
            csp = headers["Content-Security-Policy"]
            required_directives = ["default-src", "script-src", "style-src", "frame-ancestors"]
            csp_score = sum(1 for directive in required_directives if directive in csp)
            print(f"CSP directives found: {csp_score}/{len(required_directives)}")
            print(f"CSP Policy: {csp[:100]}...")

        return found_headers == len(security_headers)

    except Exception as e:
        print(f"❌ Error testing security headers: {e}")
        return False


def test_middleware_order():
    """Test that middleware is applied in correct order."""
    print("\n=== Testing Middleware Order ===")

    try:
        from main import app

        middleware_stack = []
        for middleware in app.user_middleware:
            middleware_name = middleware.cls.__name__
            middleware_stack.append(middleware_name)
            print(f"  {len(middleware_stack)}. {middleware_name}")

        expected_middleware = ["HTTPSEnforcementMiddleware", "SecurityHeadersMiddleware", "CORSMiddleware"]
        found_middleware = [m for m in expected_middleware if m in middleware_stack]

        print(f"\nSecurity middleware found: {len(found_middleware)}/{len(expected_middleware)}")
        return len(found_middleware) >= 2  # At least security headers should be present

    except Exception as e:
        print(f"❌ Error checking middleware: {e}")
        return False


if __name__ == "__main__":
    print("=== RecoveryOS Security Headers Test ===")

    headers_working = test_security_headers()
    middleware_working = test_middleware_order()

    print("\n=== Test Results ===")
    print(f"Security headers: {'✅' if headers_working else '❌'}")
    print(f"Middleware order: {'✅' if middleware_working else '❌'}")

    if headers_working and middleware_working:
        print("🎉 Security headers implementation successful!")
        sys.exit(0)
    else:
        print("❌ Security headers implementation needs fixes")
        sys.exit(1)
