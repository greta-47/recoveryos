from fastapi import APIRouter

from ..services.risk_model import explain, score

router = APIRouter(prefix="/risk", tags=["risk"])

@router.get("/score")
def get_score(
    urge: int = 3, 
    mood: int = 3, 
    sleep_hours: float = 7.0, 
    isolation: int = 2, 
    lang_signal: float = 0.0
):
    s = score(urge, mood, sleep_hours, isolation, lang_signal)
    return {"score": s, "factors": explain(urge, mood, sleep_hours, isolation, lang_signal)}
