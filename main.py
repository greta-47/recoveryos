# main.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import re
from typing import List, Union, Optional, Dict, Any

# --- Import your multi-agent pipeline (ours lives in agents/agents.py) ---
# Exposes: AgentsIn, agents_run, run_multi_agent
from agents.agents import AgentsIn as PipelineAgentsIn, agents_run as pipeline_agents_run, run_multi_agent

# If you created clinician routes, mount them here:
# from admin_clinician import router as clinician_router

# ----------------------
# Logging Setup (audit & observability)
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("recoveryos")

# ----------------------
# App & Middleware
# ----------------------
app = FastAPI(
    title="RecoveryOS API",
    version="0.1.0",
    description="AI-powered relapse prevention platform for addiction recovery",
)

# Secure CORS (tighten for prod)
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "https://recoveryos.app",
    "https://your-clinic-domain.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# If you enabled clinician routes:
# app.include_router(clinician_router)

# ----------------------
# Models (API-facing DTOs)
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1 (struggling) to 5 (strong)")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1 (low) to 5 (high)")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="Social connection: 1 (isolated) to 5 (connected)")


class AgentsRequest(BaseModel):
    """
    Public request model for /agents/run.
    Accepts OKRs as either a single string (e.g., '1) X 2) Y') or a list of strings.
    """
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: Union[str, List[str]] = Field(
        default="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%",
        description="OKRs as a single string or an array of strings",
    )
    research: Optional[str] = Field(
        default=None,
        description="Optional: if provided, the pipeline will use this instead of synthesizing lightweight research",
    )

    @validator("topic")
    def _sanitize_topic(cls, v: str) -> str:
        # Prevent obvious prompt injection / unsafe tokens
        if re.search(r"password|token|secret|PHI", v, re.I):
            raise ValueError("Invalid topic — restricted keywords detected")
        return v.strip()

    def okrs_as_list(self) -> List[str]:
        if isinstance(self.okrs, list):
            return [str(x).strip() for x in self.okrs if str(x).strip()]
        # split on numbered bullets or semicolons/commas/newlines
        raw = str(self.okrs)
        parts = re.split(r"(?:\d+\)\s*|;|,|\n)", raw)
        as_list = [p.strip(" •-") for p in parts if p and p.strip()]
        return as_list or [raw.strip()]


# ----------------------
# Routes
# ----------------------
@app.get("/", response_class=JSONResponse)
def root():
    """Health & service info."""
    return {
        "ok": True,
        "service": "RecoveryOS",
        "version": app.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": "development",
    }


@app.get("/healthz", response_class=JSONResponse)
def health():
    """Lightweight health check for load balancers and CI."""
    return {"status": "ok", "app": "RecoveryOS", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.post("/checkins")
def create_checkin(checkin: Checkin, request: Request):
    """
    Receive a daily check-in and return a personalized coping tool.
    Logs request (without PHI) for observability.
    """
    client_ip = request.client.host if request.client else "unknown"
    request_id = f"req-{hash(f'{client_ip}-{datetime.utcnow().timestamp()}') % 10**8}"

    logger.info(f"Check-in received | ID={request_id} | Urge={checkin.urge} | Mood={checkin.mood}")

    # AI Safety Guardrail: Avoid harmful or shaming language
    if checkin.urge >= 4:
        tool = "Urge Surfing — 5-minute guided wave visualization"
    elif checkin.mood <= 2:
        tool = "Grounding — 5-4-3-2-1 sensory exercise"
    elif checkin.sleep_hours < 5:
        tool = "Sleep Hygiene Tip — Try a 10-minute body scan"
    else:
        tool = "Breathing — Box breathing 4x4"

    logger.info(f"Tool suggested | ID={request_id} | Tool='{tool}'")

    return {
        "message": "Check-in received",
        "tool": tool,
        "data": checkin.dict(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
    }


@app.post("/agents/run")
def agents_run(body: AgentsRequest, request: Request):
    """
    Runs the multi-agent pipeline: Researcher → Analyst → Strategist → Advisor
    Returns all stage outputs. Outputs are de-identified and sanitized.
    """
    client_host = request.client.host if request.client else "unknown"
    request_id = f"agent-{hash(f'{client_host}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{body.topic}'")

    try:
        okrs_list = body.okrs_as_list()

        # Build pipeline input (using the pipeline's Pydantic model)
        pipeline_in = PipelineAgentsIn(
            topic=body.topic,
            horizon=body.horizon,
            okrs=okrs_list,
            research=body.research,
        )

        result: Dict[str, Any] = pipeline_agents_run(pipeline_in)  # or: run_multi_agent(...)

        # Ensure outputs are safe and de-identified (very conservative regex)
        for key in ["researcher", "analyst", "strategist", "advisor"]:
            if key in result and isinstance(result[key], str) and result[key]:
                if re.search(r"(patient\s+\d+|name\s*:|DOB\s*:)", result[key], re.I):
                    logger.warning(f"Potential PHI detected in {key} output — redacting")
                    result[key] = "[REDACTED] Output may contain sensitive data."

        logger.info(f"Agent pipeline completed | ID={request_id}")
        return {
            **result,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "okrs": okrs_list,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent pipeline failed | ID={request_id} | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")


# ----------------------
# Minimal Web UI at /ui
# ----------------------
@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<!doctype html>
<meta charset="utf-8">
<title>RecoveryOS – Multi-Agent Console</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{--bg:#0b1220;--panel:#121b2f;--muted:#94a3b8;--ink:#e6e9ef;--line:#223055;--accent:#5b8cff}
  *{box-sizing:border-box}
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);margin:0}
  .wrap{max-width:960px;margin:40px auto;padding:16px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  label{display:block;margin:10px 0 6px;color:#cbd5e1;font-size:14px}
  input,textarea,button{width:100%;padding:12px;border-radius:12px}
  input,textarea{background:#0f1627;border:1px solid #2a3b66;color:var(--ink)}
  textarea{min-height:90px}
  button{background:var(--accent);color:#fff;border:none;font-weight:600;cursor:pointer;margin-top:12px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px} @media(max-width:800px){.grid{grid-template-columns:1fr}}
  .out{white-space:pre-wrap;background:#0f1627;border:1px dashed #2a3b66;padding:12px;border-radius:12px;margin-top:16px}
  #status{color:var(--muted)}
  small{color:var(--muted)}
</style>
<div class="wrap">
  <h1>🧠 RecoveryOS – Multi-Agent Console</h1>
  <div class="card">
    <label>Topic</label>
    <input id="topic" placeholder="Top 3 underserved niches in mental health tech 2025">
    <div class="grid">
      <div><label>Horizon</label><input id="horizon" value="90 days"></div>
      <div><label>OKRs (string or JSON array)</label><input id="okrs" value='["100 beta users","80% weekly engagement","Zero safety incidents"]'></div>
    </div>
    <label>Optional: Paste external research (otherwise a lightweight summary is synthesized)</label>
    <textarea id="research" placeholder="Key facts, signals, uncertainties, constraints..."></textarea>
    <button id="run">Run Agents</button>
    <div id="status" style="margin-top:8px"></div>
    <div id="result" class="out" style="display:none"></div>
    <small>Tip: API docs at <a href="/docs" target="_blank" style="color:#a5b4fc">/docs</a></small>
  </div>
</div>
<script>
const el = (id) => document.getElementById(id);

function parseOKRs(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
  } catch(e) {}
  return raw; // server will split strings into a list
}

el("run").onclick = async () => {
  const payload = {
    topic: el("topic").value.trim() || "RecoveryOS go-to-market strategy",
    horizon: el("horizon").value.trim() || "90 days",
    okrs: parseOKRs(el("okrs").value.trim()),
    research: el("research").value.trim() || null
  };

  el("run").disabled = true;
  el("status").textContent = "Running Researcher → Analyst → Strategist → Advisor…";
  el("result").style.display = "none";

  try {
    const res = await fetch("/agents/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();
    el("status").textContent = "✅ Done.";
    el("result").style.display = "block";
    el("result").textContent =
      "► Researcher\\n\\n" + (data.researcher || "(no output)") + "\\n\\n" +
      "► Analyst\\n\\n" + (data.analyst || "(no output)") + "\\n\\n" +
      "► Strategist\\n\\n" + (data.strategist || "(no output)") + "\\n\\n" +
      "► Advisor\\n\\n" + (data.advisor || "(no output)") + "\\n\\n" +
      `[OKRs: ${(data.okrs || []).join(" | ")}]` + "\\n" +
      `[Request ID: ${data.request_id} | ${new Date().toLocaleString()}]`;
  } catch (e) {
    el("status").textContent = "❌ Error: " + (e.message || e);
  } finally {
    el("run").disabled = false;
  }
};
</script>
"""

