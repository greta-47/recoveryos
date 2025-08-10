# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# import the multi-agent pipeline
from agents import run_multi_agent

# ----------------------
# App & middleware
# ----------------------
app = FastAPI(title="RecoveryOS API", version="0.1.0")

# CORS (so the simple web UI and future sites can call your API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # TODO: tighten to your domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Models
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(ge=1, le=5)
    urge: int = Field(ge=1, le=5)
    sleep_hours: float = 0
    isolation_score: int = 0

class AgentsIn(BaseModel):
    topic: str
    horizon: str = "90 days"
    okrs: str = "1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%"

# ----------------------
# Routes
# ----------------------
@app.get("/", response_class=JSONResponse)
def root():
    return {"ok": True, "service": "RecoveryOS"}

@app.post("/checkins")
def create_checkin(checkin: Checkin):
    # super simple tool suggestion example
    tool = (
        "Urge Surfing — 5-minute guided wave visualization"
        if checkin.urge >= 4
        else "Breathing — Box breathing 4x4"
    )
    return {"message": "Check-in received", "tool": tool, "data": checkin.dict()}

@app.post("/agents/run")
def agents_run(body: AgentsIn):
    """
    Kicks off the Researcher → Analyst → Critic → Strategist pipeline
    and returns the compiled Advisor memo.
    """
    return run_multi_agent(body.topic, body.horizon, body.okrs)

# ----------------------
# Minimal web UI at /ui
# ----------------------
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
</style>
<div class="wrap">
  <h1>🧠 RecoveryOS – Multi-Agent Console</h1>
  <div class="card">
    <label>Topic</label>
    <input id="topic" placeholder="Top 3 Underserved Niches in SynBio 2025–2030">
    <div class="grid">
      <div><label>Horizon</label><input id="horizon" value="90 days"></div>
      <div><label>OKRs</label><input id="okrs" value="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%"></div>
    </div>
    <button id="run">Run Agents</button>
    <div id="status" style="margin-top:8px;color:#94a3b8"></div>
    <div id="result" class="out" style="display:none"></div>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
$("run").onclick=async()=>{
  const payload={
    topic:$("topic").value||"RecoveryOS go-to-market",
    horizon:$("horizon").value||"90 days",
    okrs:$("okrs").value||"1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%"
  };
  $("run").disabled=true;
  $("status").textContent="Running Researcher → Analyst → Critic → Strategist…";
  $("result").style.display="none";
  try{
    const res=await fetch("/agents/run",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)
    });
    if(!res.ok){ throw new Error("HTTP "+res.status); }
    const data=await res.json();
    $("status").textContent="Done.";
    $("result").style.display="block";
    $("result").textContent =
      "► Researcher\\n\\n"+(data.researcher||"(no output)")+"\\n\\n"+
      "► Analyst\\n\\n"+(data.analyst||"(no output)")+"\\n\\n"+
      "► Critic\\n\\n"+(data.critic||"(no output)")+"\\n\\n"+
      "► Strategist\\n\\n"+(data.strategist||"(no output)")+"\\n\\n"+
      "► Advisor Memo\\n\\n"+(data.advisor_memo||"(no output)");
  }catch(e){
    $("status").textContent="Error: "+(e?.message||e);
  }finally{
    $("run").disabled=false;
  }
};
</script>
"""

# No __main__ block needed; Dockerfile runs: uvicorn main:app --host 0.0.0.0 --port ${PORT}
