# admin_clinician.py
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel


# ----------------------
# Auth Placeholder (Replace with your real auth system)
# ----------------------
def get_current_user():
    """
    TODO: Replace with real auth (e.g., OAuth2/JWT/Firebase/Auth0).
    Must return a dict with at least: id, role, clinic_id.
    """
    return {"id": 1, "role": "clinician", "clinic_id": "cl-123"}


# ----------------------
# Models
# ----------------------
class TrendData(BaseModel):
    urge_avg: float
    mood_avg: float
    sleep_avg: Optional[float] = None
    checkins_last_7d: int
    last_checkin: str  # ISO 8601


class RiskFlags(BaseModel):
    rising_urge: bool
    isolation_risk: bool
    sleep_decline: bool
    engagement_drop: bool
    last_updated: str  # ISO 8601


class PatientSummary(BaseModel):
    user_id: int
    name_display: str  # e.g., "Patient J" or "Anonymous"
    enrollment_date: str  # YYYY-MM-DD
    recovery_days: int
    trend: TrendData
    risk_flags: RiskFlags
    ai_insights: Optional[Dict[str, Any]] = None  # e.g., {"summary": "...", "suggestion": "..."}
    next_action: str  # e.g., "Follow up if urge > 4"


# ----------------------
# Mock Data (replace with DB)
# ----------------------
MOCK_DATA: Dict[int, PatientSummary] = {
    101: PatientSummary(
        user_id=101,
        name_display="Patient J",
        enrollment_date="2025-06-15",
        recovery_days=54,
        trend=TrendData(
            urge_avg=2.7,
            mood_avg=3.3,
            sleep_avg=6.2,
            checkins_last_7d=6,
            last_checkin="2025-08-09T08:30:00Z",
        ),
        risk_flags=RiskFlags(
            rising_urge=False,
            isolation_risk=True,
            sleep_decline=False,
            engagement_drop=False,
            last_updated="2025-08-09T09:00:00Z",
        ),
        ai_insights={
            "summary": "Improved sleep over last 10 days correlates with lower urge scores.",
            "suggestion": "Reinforce sleep hygiene in next session.",
        },
        next_action="Send gentle check-in about social connection",
    )
}


# ----------------------
# Helpers
# ----------------------
def is_patient_in_clinic(user_id: int, clinic_id: str) -> bool:
    """
    TODO: Implement clinic scoping logic.
    For now, allow access to any patient in MOCK_DATA to simplify demos.
    """
    return user_id in MOCK_DATA


# ----------------------
# Router
# ----------------------
router = APIRouter(
    prefix="/clinician",
    tags=["clinician"],
    dependencies=[Depends(get_current_user)],  # Enforce auth for all routes
)


# ----------------------
# Routes
# ----------------------
@router.get("/patient/{user_id}/summary", response_model=PatientSummary)
def patient_summary(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Get a de-identified, clinically relevant summary for a patient.
    - Only accessible to authorized clinicians/admins
    - No PHI unless consented
    - Designed for quick triage and intervention planning
    """
    # Role check
    if current_user.get("role") not in {"clinician", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: clinicians only",
        )

    # Clinic scope check (stubbed)
    if not is_patient_in_clinic(user_id, current_user.get("clinic_id", "")):
        raise HTTPException(status_code=404, detail="Patient not found")

    patient = MOCK_DATA.get(user_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient summary not available",
        )

    return patient


@router.get("/dashboard", response_model=List[PatientSummary])
def clinician_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get a summary list of patients for this clinician (future: paginate + filter).
    Returning a list (not dict) ensures valid JSON keys and simpler clients.
    """
    # Role check
    if current_user.get("role") not in {"clinician", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: clinicians only",
        )

    # Filter by clinic scope (stubbed)
    patient_list: List[PatientSummary] = [
        p
        for uid, p in MOCK_DATA.items()
        if is_patient_in_clinic(uid, current_user.get("clinic_id", ""))
    ]
    return patient_list
