from fastapi import APIRouter
from ..services.tools_engine import suggest_tool
router = APIRouter(prefix="/tools", tags=["tools"])
@router.get("/recommend")
def recommend_tool(mood:int=3, urge:int=3, sleep_hours:float=7.0, isolation:int=2):
    return {"tool": suggest_tool(mood=mood, urge=urge, sleep_hours=sleep_hours, isolation=isolation)}
