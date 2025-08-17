from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import PlainTextResponse
from typing import Iterable, Mapping, Optional

from .settings import Settings


def build_csp(settings: Settings) -> str:
    """
    Tight, default-deny CSP. Keep this small.
    Allowlist is intentionally minimal—expand only when you truly need to.
    """
    csp_parts = {
        "default-src": "'none'",
        "base-uri": "'none'",
        "object-src": "'none'",
        "frame-ancestors": "'none'",  # pairs with X-Frame-Options
        "img-src": "'self' data: https:",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",  # allow inline styles if your UI needs it
        "font-src": "'self' data:",
        "connect-src": "'self' https:",  # API calls/websockets to HTTPS origins only
        "form-action": "'self'",
    }

    return "; ".join(f"{k} {v}" for k, v in csp_parts.items())


class SecurityHeadersMiddleware:
    """
    Adds strict security headers.
    - HSTS (only on HTTPS)
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Content-Security-Policy (or Report-Only when toggled)
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self._csp = build_csp(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = self._apply_headers(
                    message.get("headers", []),
                    scheme=_scheme_from_scope(scope),
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _apply_headers(
        self,
        existing: Iterable[Iterable[bytes]],
        scheme: str,
    ) -> list[list[bytes]]:
        hdrs: list[list[bytes]] = [list(pair) for pair in existing]

        def set_header(name: str, value: str):
            lower = name.lower().encode("ascii")
            nonlocal hdrs
            hdrs = [h for h in hdrs if h[0].lower() != lower]
            hdrs.append([name.encode("ascii"), value.encode("utf-8")])

        if scheme == "https":
            set_header(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )

        set_header("X-Frame-Options", "DENY")
        set_header("X-Content-Type-Options", "nosniff")
        set_header("Referrer-Policy", "no-referrer")

        csp_header = (
            "Content-Security-Policy-Report-Only"
            if self.settings.CSP_REPORT_ONLY
            else "Content-Security-Policy"
        )
        set_header(csp_header, self._csp)

        return hdrs


class EnforceHTTPSMiddleware:
    """
    Rejects non-HTTPS requests when ENFORCE_HTTPS=true.
    Useful if your service occasionally gets hit directly instead of
    through the TLS-terminating proxy/ALB.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.ENFORCE_HTTPS:
            await self.app(scope, receive, send)
            return

        scheme = _scheme_from_scope(scope)

        host = _get_header(scope, b"host") or ""
        is_localhost = (
            host.startswith("localhost")
            or host.startswith("127.0.0.1")
            or host.startswith("0.0.0.0")
        )

        if scheme != "https" and not is_localhost:
            resp = PlainTextResponse(
                "HTTPS required", status_code=403, headers={"Connection": "close"}
            )
            await resp(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _scheme_from_scope(scope: Scope) -> str:
    xf_proto = _get_header(scope, b"x-forwarded-proto")
    if xf_proto:
        return xf_proto.split(",")[0].strip()
    return scope.get("scheme", "http")


def _get_header(scope: Scope, name_lower_bytes: bytes) -> Optional[str]:
    for k, v in scope.get("headers", []):
        if k.lower() == name_lower_bytes:
            return v.decode("latin-1")
    return None
