from fastapi import APIRouter, Depends
from ..db import get_session
from ..schemas.checkins import CheckinIn, SuggestionOut
from ..models.checkins import Checkin
from ..services.tools_engine import suggest_tool
from ..services.risk_model import score, explain
router = APIRouter(prefix="/checkins", tags=["checkins"])
@router.post("", response_model=SuggestionOut)
def create_checkin(data: CheckinIn, session=Depends(get_session)):
    chk = Checkin(user_id=1, mood=data.mood, urge=data.urge,
                  sleep_hours=data.sleep_hours, isolation_score=data.isolation_score,
                  notes=data.notes or "")
    session.add(chk); session.commit()
    tool = suggest_tool(data.mood, data.urge, data.sleep_hours, data.isolation_score)
    s = score(data.urge, data.mood, data.sleep_hours, data.isolation_score, 0.0)
    _exp = explain(data.urge, data.mood, data.sleep_hours, data.isolation_score, 0.0)
    return SuggestionOut(message=f"Risk score: {s} — try this now.", tool=tool)
