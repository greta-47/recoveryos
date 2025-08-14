# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import re

# Import your multi-agent pipeline
from agents import run_multi_agent
from fastapi import UploadFile, File
from typing import List, Dict, Any, Optional

# Optional routers (only if present)
try:
    from coping import router as coping_router
except Exception:
    coping_router = None

try:
    from briefing import router as briefing_router
except Exception:
    briefing_router = None

# ----------------------
# Logging Setup
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("recoveryos")

try:
    from multimodal import process_multimodal_input
    from emotion_ai import analyze_emotion_and_respond
    from clinical_agents import analyze_complex_case
    from autonomous_workflows import setup_user_workflows, execute_user_workflows
except Exception as e:
    logger.warning(f"Advanced AI modules not available: {e}")
    process_multimodal_input = None
    analyze_emotion_and_respond = None
    analyze_complex_case = None
    setup_user_workflows = None
    execute_user_workflows = None


# ----------------------
# App & Middleware
# ----------------------
app = FastAPI(
    title="RecoveryOS API",
    version="0.1.0",
    description="AI-powered relapse prevention platform for addiction recovery"
)

# Secure CORS (tight)
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://recoveryos.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Serve static UI (e.g., /ui/agents.html)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

# ----------------------
# Models
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1 (struggling) to 5 (strong)")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1 (low) to 5 (high)")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="Social connection: 1 (isolated) to 5 (connected)")

class AgentsIn(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: str = Field(default="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%", max_length=500)

class EmotionalAnalysisIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[int] = None

class ClinicalCaseIn(BaseModel):
    case_data: Dict[str, Any]
    case_type: str = Field(..., description="dual_diagnosis, poly_substance, or trauma_informed")

# ----------------------
# Routes
# ----------------------
@app.get("/", response_class=JSONResponse)
def root():
    return {
        "ok": True,
        "service": "RecoveryOS",
        "version": app.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": "production"
    }

@app.get("/healthz", response_class=JSONResponse)
def health():
    return {"status": "ok", "app": "RecoveryOS", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/checkins")
def create_checkin(checkin: Checkin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    request_id = f"req-{hash(f'{client_ip}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Check-in received | ID={request_id} | Urge={checkin.urge} | Mood={checkin.mood}")

    # Safety guardrail
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
        "data": checkin.dict(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id
    }

@app.post("/agents/run")
def agents_run(body: AgentsIn, request: Request):
    client_host = request.client.host if request.client else 'unknown'
    request_id = f"agent-{hash(f'{client_host}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{body.topic}'")
    try:
        # Prompt injection safety
        if re.search(r"password|token|secret|PHI", body.topic, re.I):
            raise HTTPException(status_code=400, detail="Invalid topic — restricted keywords detected")

        user_context = {"user_id": "anonymous"}
        result = run_multi_agent(body.topic, body.horizon, body.okrs, user_context)

        # De-identification scan
        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key in result and result[key]:
                if re.search(r"patient \d+|name:|DOB:", result[key], re.I):
                    logger.warning(f"Potential PHI detected in {key} output — redacting")
                    result[key] = "[REDACTED] Output may contain sensitive data."

        logger.info(f"Agent pipeline completed | ID={request_id}")
        return {**result, "request_id": request_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent pipeline failed | ID={request_id} | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")

@app.post("/ai/emotion-analysis")
def emotion_analysis(body: EmotionalAnalysisIn):
    if not analyze_emotion_and_respond:
        raise HTTPException(status_code=503, detail="Emotional AI not available")
    
    try:
        user_context = {"user_id": body.user_id} if body.user_id else {}
        result = analyze_emotion_and_respond(body.text, user_context)
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Emotion analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Emotion analysis failed")

@app.post("/ai/clinical-analysis")
def clinical_analysis(body: ClinicalCaseIn):
    if not analyze_complex_case:
        raise HTTPException(status_code=503, detail="Clinical AI not available")
    
    try:
        result = analyze_complex_case(body.case_data)
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Clinical analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Clinical analysis failed")

@app.post("/ai/multimodal-upload")
async def multimodal_upload(file: UploadFile = File(...)):
    if not process_multimodal_input:
        raise HTTPException(status_code=503, detail="Multimodal processing not available")
    
    try:
        file_data = await file.read()
        result = process_multimodal_input(file_data, file.filename, file.content_type)
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Multimodal processing failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Multimodal processing failed")

@app.post("/workflows/setup/{user_id}")
def setup_workflows(user_id: int, preferences: Dict[str, Any]):
    if not setup_user_workflows:
        raise HTTPException(status_code=503, detail="Autonomous workflows not available")
    
    try:
        workflow_ids = setup_user_workflows(user_id, preferences)
        return {
            "user_id": user_id,
            "workflow_ids": workflow_ids,
            "message": f"Set up {len(workflow_ids)} workflows",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Workflow setup failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Workflow setup failed")

@app.post("/workflows/execute/{user_id}")
def execute_workflows(user_id: int, context: Dict[str, Any]):
    if not execute_user_workflows:
        raise HTTPException(status_code=503, detail="Autonomous workflows not available")
    
    try:
        results = execute_user_workflows(user_id, context)
        return {
            "user_id": user_id,
            "workflow_results": results,
            "executed_count": len(results),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Workflow execution failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")

# Optional routers
if coping_router:
    app.include_router(coping_router)
if briefing_router:
    app.include_router(briefing_router)

