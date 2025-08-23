"""
main.py — RecoveryOS API (refactor, copy-paste ready)

- Env-driven config (APP_NAME, APP_VERSION, API_KEY, CORS_ORIGINS)
- Structured JSON logging with request IDs + safe client fingerprinting
- Optional API key auth via X-API-Key (disable by omitting API_KEY)
- /healthz, /checkins, /agents/run endpoints
- Guardrails: prompt-injection filter, PHI redaction
- Optional routers: coping, briefing(s)
- Static UI mounting if 'ui/' exists
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ----------------------
# Settings
# ----------------------
APP_NAME = os.getenv("APP_NAME", "RecoveryOS API")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
API_KEY = os.getenv("API_KEY")
ALLOWED_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o]


# ----------------------
# Structured logging
# ----------------------
class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": int(time.time() * 1000),
        }
        # Allow structured extras via record.extra dict
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base)


logger = logging.getLogger("recoveryos")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(JsonLogFormatter())
    logger.addHandler(_h)


# ----------------------
# Utils
# ----------------------
def safe_client_fingerprint(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    coarse_ts = int(time.time() // 60)
    h = blake2b(digest_size=8)
    h.update(f"{host}-{coarse_ts}".encode())
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


# ----------------------
# Optional imports
# ----------------------
try:
    from agents import run_multi_agent  # type: ignore
except Exception:
    run_multi_agent = None  # type: ignore[assignment]

try:
    from coping import router as coping_router  # type: ignore
except Exception:
    coping_router = None  # type: ignore[assignment]

# Support either file name: briefings.py or briefing.py
briefing_router = None
try:
    from briefings import router as _briefings_router  # type: ignore

    briefing_router = _briefings_router
except Exception:
    try:
        from briefing import router as _briefing_router  # type: ignore

        briefing_router = _briefing_router
    except Exception:
        briefing_router = None  # type: ignore[assignment]


# ----------------------
# Auth
# ----------------------
def api_key_auth(x_api_key: Optional[str] = Header(default=None)) -> None:
    # If API_KEY is not set, auth is disabled
    if API_KEY is None:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ----------------------
# App & Middleware
# ----------------------
app = FastAPI(title=APP_NAME, version=APP_VERSION, description="AI-powered relapse prevention platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

if os.path.isdir("ui"):
    app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


# ----------------------
# Models
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1 (struggling) to 5 (strong)")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1 (low) to 5 (high)")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="Social connection: 0 (isolated) to 5 (connected)")


class AgentsIn(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: str = Field(
        default="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%",
        max_length=500,
    )


# ----------------------
# Middleware (request/response logging with request ID)
# ----------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    client_fp = safe_client_fingerprint(request)
    logger.info(
        "request",
        extra={
            "extra": {
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
                "client_fp": client_fp,
            }
        },
    )
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "response",
            extra={
                "extra": {
                    "path": request.url.path,
                    "status": response.status_code,
                    "request_id": request_id,
                    "client_fp": client_fp,
                }
            },
        )
        return response
    except Exception:
        logger.exception(
            "unhandled_error",
            extra={"extra": {"path": request.url.path, "request_id": request_id, "client_fp": client_fp}},
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"type": "server_error", "message": "Unexpected error", "request_id": request_id}},
        )


# ----------------------
# Exception handlers
# ----------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Invalid request payload",
                "fields": exc.errors(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"type": "http_error", "message": exc.detail, "request_id": request_id}},
    )


# ----------------------
# Routes
# ----------------------
@app.get("/", response_class=JSONResponse)
def root():
    return {"ok": True, "service": APP_NAME, "version": APP_VERSION, "timestamp": now_iso()}


@app.get("/healthz", response_class=JSONResponse)
def health():
    return {"status": "ok", "app": APP_NAME, "timestamp": now_iso()}


@app.post("/checkins", dependencies=[Depends(api_key_auth)])
def create_checkin(checkin: Checkin, request: Request):
    request_id = str(uuid.uuid4())
    if checkin.urge >= 4:
        tool = "Urge Surfing — 5-minute guided wave visualization"
    elif checkin.mood <= 2:
        tool = "Grounding — 5-4-3-2-1 sensory exercise"
    elif checkin.sleep_hours < 5:
        tool = "Sleep Hygiene Tip: Try a 10-minute body scan"
    else:
        tool = "Breathing — Box breathing 4x4"
    logger.info(
        "checkin",
        extra={
            "extra": {
                "request_id": request_id,
                "urge": checkin.urge,
                "mood": checkin.mood,
                "tool": tool,
                "client_fp": safe_client_fingerprint(request),
            }
        },
    )
    return {
        "message": "Check-in received",
        "tool": tool,
        "data": checkin.dict(),
        "timestamp": now_iso(),
        "request_id": request_id,
    }


@app.post("/agents/run", dependencies=[Depends(api_key_auth)])
def agents_run(body: AgentsIn, request: Request):
    request_id = str(uuid.uuid4())
    if run_multi_agent is None:
        raise HTTPException(status_code=503, detail="Agent pipeline unavailable")
    # Simple prompt-injection / sensitive term guard
    if re.search(r"password|token|secret|PHI", body.topic, re.I):
        raise HTTPException(status_code=400, detail="Invalid topic — restricted keywords detected")
    try:
        result = run_multi_agent(body.topic, body.horizon, body.okrs)
        # De-identification scan
        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key in result and isinstance(result[key], str):
                if re.search(r"patient \d+|name:|DOB:", result[key], re.I):
                    logger.warning("PHI detected", extra={"extra": {"request_id": request_id, "field": key}})
                    result[key] = "[REDACTED] Output may contain sensitive data."
        return {**result, "request_id": request_id, "timestamp": now_iso()}
    except Exception:
        logger.exception("agent_error", extra={"extra": {"request_id": request_id}})
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")


# ----------------------
# Optional routers
# ----------------------
if coping_router:
    app.include_router(coping_router)
if briefing_router:
    app.include_router(briefing_router)

# ----------------------
# Optional metrics (soft dependency)
# ----------------------
try:
    from starlette_exporter import PrometheusMiddleware, handle_metrics  # type: ignore

    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", handle_metrics)
except Exception:

    @app.get("/metrics", include_in_schema=False)
    async def metrics_placeholder():
        return PlainTextResponse("starlette_exporter not installed")


# ----------------------
# Entrypoint
# ----------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        proxy_headers=True,
    )
