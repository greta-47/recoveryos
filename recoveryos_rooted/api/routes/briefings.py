from fastapi import APIRouter

router = APIRouter(prefix="/briefings", tags=["briefings"])
@router.post("/weekly:run")
def run_weekly_briefing():
    return {"ok": True, "status": "simulated send"}
