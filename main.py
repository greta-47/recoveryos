# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import re
import os, sys

# Ensure current dir is importable
sys.path.append(os.getcwd())

# ----------------------
# Logging
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("recoveryos")

# ----------------------
# App
# ----------------------
app = FastAPI(
    title="RecoveryOS API",
    version="0.1.0",
    description="AI-powered relapse prevention platform for addiction recovery"
)

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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ----------------------
# Optional router loader (won’t crash if a file is missing)
# ----------------------
def _try_include(module_name: str, attr: str = "router", friendly: str = ""):
    try:
        mod = __import__(module_name, fromlist=[attr])
        app.include_router(getattr(mod, attr))
        logger.info("Loaded router: %s", friendly or module_name)
    except Exception as e:
        logger.warning("Router not loaded (%s): %s", friendly or module_name, e)

# Load your routers (top-level files present in your repo)
_try_include("coping", friendly="coping")
_try_include("briefings", friendly="briefings")           # <-- plural
_try_include("admin_clinician", friendly="admin_clinician")

# Agents pipeline import (safe fallback)
try:
    from agents import run_multi_agent
except Exception as e:
    logger.error("Failed to import agents.run_multi_agent: %s", e)
    def run_multi_agent(*args, **kwargs):
        raise HTTPException(status_code=500, detail="Agents module not available")

# ----------------------
# Demo models / routes
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1 (struggling) to 5 (strong)")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1 (low) to 5 (high)")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="Social connection: 1 (isolated) to 5 (connected)")

class AgentsIn(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: str = Field(default="1) 100 beta users 2) 80% engagement 3) Zero safety incidents", max_length=500)

@app.get("/", response_class=JSONResponse)
def root():
    return {
        "ok": True,
        "service": "RecoveryOS",
        "version": app.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": os.getenv("ENV", "development"),
    }

@app.get("/healthz", response_class=JSONResponse)
def health():
    return {"status": "ok", "app": "RecoveryOS", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/checkins")
def create_checkin(checkin: Checkin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    request_id = f"req-{hash(f'{client_ip}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Check-in received | ID={request_id} | Urge={checkin.urge} | Mood={checkin.mood}")

    if checkin.urge >= 4:
        tool = "Urge Surfing — 5-minute guided wave visualization"
    elif checkin.mood <= 2:
        tool = "Grounding — 5-4-3-2-1 sensory exercise"
    elif checkin.sleep_hours < 5:
        tool = "Sleep Hygiene Tip: Try a 10-minute body scan"
    else:
        tool = "Breathing — Box breathing 4x4"

    logger.info(f"Tool suggested | ID={request_id} | Tool='{tool}'")
    return {
        "message": "Check-in received",
        "tool": tool,
        "data": checkin.model_dump(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
    }

@app.post("/agents/run")
def agents_run(body: AgentsIn, request: Request):
    rid_src = request.client.host if request.client else "unknown"
    request_id = f"agent-{hash(f'{rid_src}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{body.topic}'")

    try:
        if re.search(r"password|token|secret|PHI", body.topic, re.I):
            raise HTTPException(status_code=400, detail="Invalid topic — restricted keywords detected")

        result = run_multi_agent(body.topic, body.horizon, body.okrs)

        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key in result and result[key]:
                if re.search(r"patient \d+|name:|DOB:", str(result[key]), re.I):
                    logger.warning(f"Potential PHI detected in {key} output — redacting")
                    result[key] = "[REDACTED] Output may contain sensitive data."

        logger.info(f"Agent pipeline completed | ID={request_id}")
        return {**result, "request_id": request_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent pipeline failed | ID={request_id} | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<!doctype html>
<meta charset="utf-8">
<title>RecoveryOS – Multi-Agent Console</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0b1220;color:#e6e9ef;margin:0}
  .wrap{max-width:900px;margin:40px auto;padding:16px}
  .card{background:#121b2f;border:1px solid #223055;border-radius:16px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  label{display:block;margin:10px 0 4px;color:#cbd5e1}
  input,button{width:100%;padding:12px;border-radius:12px}
  input{background:#0f1627;border:1px solid #2a3b66;color:#e6e9ef}
  button{background:#5b8cff;color:#fff;border:none;font-weight:600;cursor:pointer;margin-top:12px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px} @media(max-width:800px){.grid{grid-template-columns:1fr}}
  .out{white-space:pre-wrap;background:#0f1627;border:1px dashed #2a3b66;padding:12px;border-radius:12px;margin-top:16px}
  #status{color:#94a3b8}
</style>
<div class="wrap">
  <h1>🧠 RecoveryOS – Multi-Agent Console</h1>
  <div class="card">
    <label>Topic</label>
    <input id="topic" placeholder="Top 3 Underserved Niches in Mental Health Tech 2025">
    <div class="grid">
      <div><label>Horizon</label><input id="horizon" value="90 days"></div>
      <div><label>OKRs</label><input id="okrs" value="1) 100 beta users 2) 80% engagement 3) Zero safety incidents"></div>
    </div>
    <button id="run">Run Agents</button>
    <div id="status" style="margin-top:8px"></div>
    <div id="result" class="out" style="display:none"></div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
$("run").onclick = async () => {
  const payload = {
    topic: $("topic").value.trim() || "RecoveryOS go-to-market strategy",
    horizon: $("horizon").value.trim() || "90 days",
    okrs: $("okrs").value.trim() || "1) 100 beta users 2) 80% engagement 3) Zero safety incidents"
  };
  $("run").disabled = true;
  $("status").textContent = "Running Researcher → Analyst → Critic → Strategist…";
  $("result").style.display = "none";
  try {
    const res = await fetch("/agents/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    $("status").textContent = "✅ Done.";
    $("result").style.display = "block";
    $("result").textContent =
      "► Researcher\\n\\n" + (data.researcher || "(no output)") + "\\n\\n" +
      "► Analyst\\n\\n" + (data.analyst || "(no output)") + "\\n\\n" +
      "► Critic\\n\\n" + (data.critic || "(no output)") + "\\n\\n" +
      "► Strategist\\n\\n" + (data.strategist || "(no output)") + "\\n\\n" +
      "► Advisor Memo\\n\\n" + (data.advisor_memo || "(no output)") + "\\n\\n" +
      `[Request ID: ${data.request_id} | ${new Date().toLocaleString()}]`;
  } catch (e) {
    $("status").textContent = "❌ Error: " + (e.message || e);
  } finally {
    $("run").disabled = false;
  }
};
</script>
"""
