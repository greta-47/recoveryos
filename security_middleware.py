"""
Security middleware for RecoveryOS API.
Implements HTTPS security headers and enforcement.
"""
import os
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("recoveryos")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.
    Implements HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy.
    """
    
    def __init__(self, app, csp_mode: str = "enforce"):
        super().__init__(app)
        self.csp_mode = csp_mode  # "enforce" or "report-only"
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add all required security headers to the response."""
        
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        response.headers["X-Frame-Options"] = "DENY"
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        csp_policy = self._build_csp_policy()
        
        if self.csp_mode == "report-only":
            response.headers["Content-Security-Policy-Report-Only"] = csp_policy
            logger.debug("Applied CSP in report-only mode")
        else:
            response.headers["Content-Security-Policy"] = csp_policy
            logger.debug("Applied CSP in enforce mode")
        
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        logger.debug(f"Applied security headers to {request.url.path}")
    
    def _build_csp_policy(self) -> str:
        """
        Build Content Security Policy based on application needs.
        Restrictive policy for RecoveryOS API.
        """
        policy_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Allow inline scripts for FastAPI docs
            "style-src 'self' 'unsafe-inline'",   # Allow inline styles for FastAPI docs
            "img-src 'self' data: https:",        # Allow images from self, data URLs, and HTTPS
            "font-src 'self'",
            "connect-src 'self'",                 # API calls to same origin
            "media-src 'none'",                   # No media content expected
            "object-src 'none'",                  # No plugins
            "frame-src 'none'",                   # No frames
            "base-uri 'self'",                    # Restrict base tag
            "form-action 'self'",                 # Forms only to same origin
            "frame-ancestors 'none'",             # Prevent embedding
            "upgrade-insecure-requests"           # Upgrade HTTP to HTTPS
        ]
        
        report_uri = os.getenv("CSP_REPORT_URI")
        if report_uri:
            policy_parts.append(f"report-uri {report_uri}")
        
        return "; ".join(policy_parts)


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces HTTPS connections.
    Allows localhost exemption for development.
    """
    
    def __init__(self, app, allow_localhost: bool = True):
        super().__init__(app)
        self.allow_localhost = allow_localhost
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._should_enforce_https(request):
            https_url = request.url.replace(scheme="https")
            logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
            return Response(
                status_code=301,
                headers={"Location": str(https_url)}
            )
        
        return await call_next(request)
    
    def _should_enforce_https(self, request: Request) -> bool:
        """Determine if HTTPS should be enforced for this request."""
        
        if request.url.scheme == "https":
            return False
        
        if self.allow_localhost:
            host = request.url.hostname
            if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
                return False
        
        if request.url.path in ["/healthz", "/health", "/metrics"]:
            return False
        
        return True


def get_security_config():
    """Get security configuration from environment variables."""
    return {
        "csp_mode": os.getenv("CSP_MODE", "enforce"),  # "enforce" or "report-only"
        "allow_localhost": os.getenv("ALLOW_LOCALHOST", "true").lower() == "true",
        "enable_https_enforcement": os.getenv("ENABLE_HTTPS_ENFORCEMENT", "true").lower() == "true"
    }
