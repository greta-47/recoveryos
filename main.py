"""
main.py — RecoveryOS API (refactor Option B, copy-paste ready)

- Env-driven config (APP_NAME, APP_VERSION, API_KEY, CORS_ORIGINS)
- Structured JSON logging with request IDs + safe client fingerprinting
- Optional API key auth via X-API-Key (disable by omitting API_KEY)
- /healthz, /checkins, /agents/run endpoints
- Guardrails: prompt-injection filter, PHI redaction
- Optional routers: coping, briefing
- Static UI mounting if folder exists
"""
import os
import re
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# Import your multi-agent pipeline
try:
    from agents import run_multi_agent
except Exception:
    run_multi_agent = None

# Optional routers
try:
    from coping import router as coping_router
except Exception:
    coping_router = None

try:
    from briefing import router as briefing_router
except Exception:
    briefing_router = None

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
APP_NAME = os.getenv("APP_NAME", "RecoveryOS API")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
API_KEY = os.getenv("API_KEY")
ALLOWED_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o]
CSP_MODE = os.getenv("CSP_MODE", "report-only")

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": int(time.time() * 1000),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base)

logger = logging.getLogger("recoveryos")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(JsonLogFormatter())
    logger.addHandler(h)

# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------
def safe_client_fingerprint(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    coarse_ts = int(time.time() // 60)
    h = blake2b(digest_size=8)
    h.update(f"{host}-{coarse_ts}".encode())
    return h.hexdigest()

def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

# ---------------------------------------------------------------------------
# Security Middleware
# ---------------------------------------------------------------------------
CSP_POLICY = {
    "default-src": "'self'",
    "img-src": ["'self'", "data:", "https://fastapi.tiangolo.com"],
    "connect-src": "'self'",
    "script-src": "'self'",
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src-elem": [
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    ],
    "style-src-elem": [
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    ],
}

def parse_csp_policy(policy: dict) -> str:
    policies = []
    for directive, values in policy.items():
        if isinstance(values, list):
            values = " ".join(values)
        policies.append(f"{directive} {values}")
    return "; ".join(policies)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, csp_mode: str = "enforce"):
        super().__init__(app)
        self.csp_mode = csp_mode
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff", 
            "Referrer-Policy": "no-referrer",
        }
        
        csp_policy = parse_csp_policy(CSP_POLICY)
        if self.csp_mode == "report-only":
            headers["Content-Security-Policy-Report-Only"] = csp_policy
        else:
            headers["Content-Security-Policy"] = csp_policy
            
        response.headers.update(headers)
        return response

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def api_key_auth(x_api_key: Optional[str] = Header(default=None)) -> None:
    if API_KEY is None:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title=APP_NAME, version=APP_VERSION, description="AI-powered relapse prevention platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

app.add_middleware(SecurityHeadersMiddleware, csp_mode=CSP_MODE)

if os.path.isdir("ui"):
    app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5)
    urge: int = Field(..., ge=1, le=5)
    sleep_hours: float = Field(0, ge=0, le=24)
    isolation_score: int = Field(0, ge=0, le=5)

class AgentsIn(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: str = Field(default="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%", max_length=500)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    client_fp = safe_client_fingerprint(request)
    logger.info("request", extra={"extra": {"path": request.url.path, "method": request.method, "request_id": request_id, "client_fp": client_fp}})
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("response", extra={"extra": {"path": request.url.path, "status": response.status_code, "request_id": request_id, "client_fp": client_fp}})
        return response
    except Exception:
        logger.exception("unhandled_error", extra={"extra": {"path": request.url.path, "request_id": request_id, "client_fp": client_fp}})
        return JSONResponse(status_code=500, content={"error": {"type": "server_error", "message": "Unexpected error", "request_id": request_id}})

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(status_code=422, content={"error": {"type": "validation_error", "message": "Invalid request payload", "fields": exc.errors(), "request_id": request_id}})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(status_code=exc.status_code, content={"error": {"type": "http_error", "message": exc.detail, "request_id": request_id}})

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
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
    logger.info("checkin", extra={"extra": {"request_id": request_id, "urge": checkin.urge, "mood": checkin.mood, "tool": tool, "client_fp": safe_client_fingerprint(request)}})
    return {"message": "Check-in received", "tool": tool, "data": checkin.dict(), "timestamp": now_iso(), "request_id": request_id}

@app.post("/agents/run", dependencies=[Depends(api_key_auth)])
def agents_run(body: AgentsIn, request: Request):
    request_id = str(uuid.uuid4())
    if run_multi_agent is None:
        raise HTTPException(status_code=503, detail="Agent pipeline unavailable")
    if re.search(r"password|token|secret|PHI", body.topic, re.I):
        raise HTTPException(status_code=400, detail="Invalid topic — restricted keywords detected")
    try:
        result = run_multi_agent(body.topic, body.horizon, body.okrs)
        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key in result and isinstance(result[key], str):
                if re.search(r"patient \\d+|name:|DOB:", result[key], re.I):
                    logger.warning("PHI detected", extra={"extra": {"request_id": request_id, "field": key}})
                    result[key] = "[REDACTED] Output may contain sensitive data."
        return {**result, "request_id": request_id, "timestamp": now_iso()}
    except Exception as e:
        logger.exception("agent_error", extra={"extra": {"request_id": request_id}})
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")

# Optional routers
if coping_router:
    app.include_router(coping_router)
if briefing_router:
    app.include_router(briefing_router)

# Optional metrics (soft dependency)
try:
    from starlette_exporter import PrometheusMiddleware, handle_metrics
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", handle_metrics)
except Exception:
    @app.get("/metrics", include_in_schema=False)
    async def metrics_placeholder():
        return PlainTextResponse("starlette_exporter not installed")

# Entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True, proxy_headers=True)
