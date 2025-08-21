import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

REQUIRED_SECURITY_HEADERS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}

CSP_HEADERS = ["content-security-policy", "content-security-policy-report-only"]

def test_security_headers_root():
    """Test security headers on root endpoint /"""
    response = client.get("/")
    assert response.status_code == 200
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value
    
    csp_present = any(header in response.headers for header in CSP_HEADERS)
    assert csp_present, "Content-Security-Policy header missing"

def test_security_headers_healthz():
    """Test security headers on health endpoint /healthz"""
    response = client.get("/healthz")
    assert response.status_code == 200
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value
    
    csp_present = any(header in response.headers for header in CSP_HEADERS)
    assert csp_present, "Content-Security-Policy header missing"

def test_security_headers_checkins():
    """Test security headers on checkins endpoint /checkins"""
    response = client.post("/checkins", json={
        "mood": 3,
        "urge": 2,
        "sleep_hours": 7.5,
        "isolation_score": 1
    })
    assert response.status_code in [200, 401]
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value
    
    csp_present = any(header in response.headers for header in CSP_HEADERS)
    assert csp_present, "Content-Security-Policy header missing"

def test_security_headers_agents_run():
    """Test security headers on agents endpoint /agents/run"""
    response = client.post("/agents/run", json={
        "topic": "test topic for security headers",
        "horizon": "90 days",
        "okrs": "test okrs"
    })
    assert response.status_code in [200, 401, 503]
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value
    
    csp_present = any(header in response.headers for header in CSP_HEADERS)
    assert csp_present, "Content-Security-Policy header missing"

def test_csp_policy_content():
    """Test that CSP policy contains required directives"""
    response = client.get("/")
    
    csp_value = None
    for header in CSP_HEADERS:
        if header in response.headers:
            csp_value = response.headers[header]
            break
    
    assert csp_value is not None, "No CSP header found"
    
    assert "default-src 'self'" in csp_value
    assert "style-src 'self' 'unsafe-inline'" in csp_value
    assert "img-src 'self' data:" in csp_value
    assert "connect-src 'self'" in csp_value
    assert "script-src 'self'" in csp_value

def test_docs_endpoint_accessible():
    """Test that /docs endpoint is accessible and returns HTML"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "swagger" in response.text.lower()
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value

def test_redoc_endpoint_accessible():
    """Test that /redoc endpoint is accessible and returns HTML"""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "redoc" in response.text.lower()
    
    for header_name, expected_value in REQUIRED_SECURITY_HEADERS.items():
        assert header_name in response.headers
        assert response.headers[header_name] == expected_value

def test_csp_mode_environment_control():
    """Test that CSP mode can be controlled via environment"""
    import os
    from main import SecurityHeadersMiddleware, parse_csp_policy, CSP_POLICY
    
    middleware_report = SecurityHeadersMiddleware(app, csp_mode="report-only")
    assert middleware_report.csp_mode == "report-only"
    
    middleware_enforce = SecurityHeadersMiddleware(app, csp_mode="enforce")
    assert middleware_enforce.csp_mode == "enforce"
    
    csp_string = parse_csp_policy(CSP_POLICY)
    assert isinstance(csp_string, str)
    assert "default-src 'self'" in csp_string
