import os
from typing import Callable, Awaitable
from starlette.types import ASGIApp, Receive, Scope, Send


def _build_csp() -> str:
    app_origin = os.getenv("CSP_APP_ORIGIN", "https://app.my-domain.com").strip()
    cdn_list = [c.strip() for c in os.getenv("CSP_CDN_LIST", "").split(",") if c.strip()]
    sources = ["'self'"]
    if app_origin:
        sources.append(app_origin)
    sources += cdn_list
    src = " ".join(sources)
    parts = [
        f"default-src {src}",
        f"script-src {src}",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        f"connect-src {src}",
        f"img-src {src} data:",
        f"style-src {src}",
        f"font-src {src}",
    ]
    return "; ".join(parts)


class ContentSecurityPolicyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.header_name = (
            b"content-security-policy-report-only"
            if os.getenv("CSP_REPORT_ONLY", "false").lower() in ("1", "true", "yes")
            else b"content-security-policy"
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        csp_value = _build_csp().encode("utf-8")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((self.header_name, csp_value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
