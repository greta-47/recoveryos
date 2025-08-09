from fastapi import APIRouter
router = APIRouter(prefix="/clinician", tags=["clinician"])
@router.get("/patient/{user_id}/summary")
def patient_summary(user_id:int):
    return {"user_id": user_id, "trend": {"urge_avg": 2.7, "mood_avg": 3.3}}
