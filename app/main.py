from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from .settings import Settings
from .security_middleware import SecurityHeadersMiddleware, EnforceHTTPSMiddleware

settings = Settings()

app = FastAPI(title="RecoveryOS API", version=os.getenv("VERSION", "0"))

app.add_middleware(EnforceHTTPSMiddleware, settings=settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS] if settings.ALLOWED_ORIGINS else [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

app.add_middleware(SecurityHeadersMiddleware, settings=settings)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"ok": True}


# Serve static UI (e.g., /ui/agents.html)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
