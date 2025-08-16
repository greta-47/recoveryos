import re
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

# Import your multi-agent pipeline
from agents import run_multi_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="RecoveryOS API", version="0.1.0")

# ----------- Models -----------
class AgentsIn(BaseModel):
    topic: str
    horizon: Optional[str] = None
    okrs: Optional[List[str]] = None

# ----------- Routes -----------

@app.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.post("/agents/run")
def agents_run(body: AgentsIn, request: Request):
    client_host = request.client.host if request.client else "unknown"
    request_id = f"agent-{hash(f'{client_host}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{body.topic}'")

    try:
        # Prompt injection / secret guard
        if re.search(r"password|token|secret|PHI", body.topic, re.I):
            raise HTTPException(
                status_code=400,
                detail="Invalid topic — restricted keywords detected"
            )

        # Optional: minimal per-request context
        user_context = {"user_id": "anonymous"}

        # Run multi-agent pipeline (topic, horizon, okrs, context)
        result = run_multi_agent(body.topic, body.horizon, body.okrs, user_context)

        # De-identification scan (defense-in-depth)
        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key i

