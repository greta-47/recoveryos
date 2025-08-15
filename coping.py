# coping.py
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict
from datetime import datetime
import os
import logging

try:
    from alerts import queue_clinician_alert
except Exception:  # fallback if alerts.py missing during local tests

    def queue_clinician_alert(*args, **kwargs):
        pass


logger = logging.getLogger("recoveryos")

RISK_HIGH_THRESHOLD = float(os.getenv("RISK_HIGH_THRESHOLD", "7.0"))


# ----------------------
# Models
# ----------------------
class CopingRequest(BaseModel):
    mood: int = Field(3, ge=1, le=5, description="1=struggling, 5=strong")
    urge: int = Field(3, ge=1, le=5, description="1=low, 5=high")
    sleep_hours: float = Field(7.0, ge=0, le=24, description="Hours slept last night")
    isolation: int = Field(3, ge=1, le=5, description="1=isolated, 5=connected")
    energy: int = Field(3, ge=1, le=5, description="1=exhausted, 5=energized")
    craving_type: Optional[
        Literal["alcohol", "opioid", "stimulant", "benzo", "other"]
    ] = Field(None, description="Substance the urge is for (if known)")
    context: Optional[str] = Field(
        None,
        max_length=200,
        description="Brief context (avoid PHI: no names, locations)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mood": 2,
                    "urge": 5,
                    "sleep_hours": 5.0,
                    "isolation": 1,
                    "energy": 1,
                    "craving_type": "stimulant",
                    "context": "After argument with partner",
                }
            ]
        }
    }


class CopingResponse(BaseModel):
    tool: str = Field(..., description="Name of the coping skill")
    description: str = Field(..., description="How to do it (1–2 sentences)")
    category: Literal[
        "grounding",
        "breathing",
        "distraction",
        "connection",
        "body-scan",
        "mindfulness",
        "professional-help",
    ] = Field(..., description="Type of tool")
    urgency_level: Literal["low", "moderate", "high"] = Field(
        "moderate", description="For routing logic"
    )
    suggested_duration: str = Field(
        "5 minutes", description="Recommended time to spend"
    )
    message: str = Field(..., description="Personalized encouragement")
    timestamp: str = Field(
        default_factory=lambda: f"{datetime.utcnow().isoformat()}Z",
        description="UTC timestamp",
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Optional: links to videos, audio, or handouts",
    )

    # For UI + alerts
    risk_score: float = Field(0.0, ge=0, le=10, description="0–10 composite risk score")
    risk_level: Literal["Low", "Moderate", "High", "Severe"] = Field(
        "Low", description="Discrete risk level"
    )
    risk_factors: List[Dict] = Field(
        default_factory=list, description="Top contributing factors"
    )


router = APIRouter(prefix="/coping", tags=["coping"])


# ----------------------
# Minimal rule-based engine + risk model (stub)
# ----------------------
def _risk_analyze(mood: int, urge: int, isolation: int, energy: int) -> Dict:
    # very simple composite
    score = (
        (urge * 1.8)
        + max(0, 3 - mood) * 0.8
        + max(0, 3 - isolation) * 0.6
        + max(0, 3 - energy) * 0.6
    )
    score = max(0.0, min(10.0, score))
    if score >= 9:
        level = "Severe"
    elif score >= 7:
        level = "High"
    elif score >= 4:
        level = "Moderate"
    else:
        level = "Low"
    factors = []
    if urge >= 4:
        factors.append(
            {
                "name": "High Urge",
                "impact": 0.8,
                "explanation": "Self-reported urge is high (≥4).",
            }
        )
    if mood <= 2:
        factors.append(
            {"name": "Low Mood", "impact": 0.5, "explanation": "Mood is low (≤2)."}
        )
    if isolation <= 2:
        factors.append(
            {
                "name": "Isolation",
                "impact": 0.4,
                "explanation": "Social connection is low (≤2).",
            }
        )
    if energy <= 2:
        factors.append(
            {
                "name": "Exhaustion",
                "impact": 0.3,
                "explanation": "Energy level is very low (≤2).",
            }
        )
    return {"score": round(score, 1), "level": level, "factors": factors[:3]}


def _suggest_tool(
    mood: int,
    urge: int,
    sleep_hours: float,
    isolation: int,
    energy: int,
    craving_type: Optional[str],
) -> Dict:
    tool = "Box Breathing"
    description = "Inhale 4s, hold 4s, exhale 4s, hold 4s. Repeat for 5 minutes."
    category = "breathing"
    urgency_level = "low"
    suggested_duration = "5 minutes"
    message = "You’re not alone. This simple breath can help you reset."

    if urge >= 4:
        urgency_level = "high"
        if craving_type == "opioid":
            tool = "Urge Surfing"
            description = "Visualize the urge as a wave. It rises, peaks, and falls. Ride it without acting."
            category = "grounding"
            suggested_duration = "5–7 minutes"
            message = "This urge will pass. Surf it; you don’t have to act on it."
        elif energy <= 2:
            tool = "Progressive Muscle Relaxation"
            description = "Tense and release each muscle group from toes to head."
            category = "body-scan"
            message = "When exhaustion meets craving, this can help your body let go."
        else:
            tool = "5-4-3-2-1 Grounding"
            description = "Name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste."
            category = "grounding"
            message = (
                "You’re here. You’re safe. Use your senses to return to the present."
            )
    elif mood <= 2 and isolation <= 2:
        urgency_level = "moderate"
        tool = "Reach Out Script"
        description = "Text a trusted person: 'I’m having a tough moment. Can I talk for 5 minutes?'"
        category = "connection"
        suggested_duration = "10 minutes"
        message = "Connection is medicine. One sentence can shift the weight."
    elif sleep_hours < 5:
        urgency_level = "moderate"
        tool = "Body Scan Meditation"
        description = (
            "Scan attention from toes to head, noticing tension without judgment."
        )
        category = "mindfulness"
        suggested_duration = "10 minutes"
        message = (
            "When sleep feels far away, this can help your body relax enough to rest."
        )

    return {
        "tool": tool,
        "description": description,
        "category": category,
        "urgency_level": urgency_level,
        "suggested_duration": suggested_duration,
        "message": message,
        "resources": (
            ["https://recoveryos.app/guided/urge-surfing.mp3"]
            if category == "grounding"
            else []
        ),
    }


# ----------------------
# Routes
# ----------------------
@router.post("/recommend", response_model=CopingResponse)
def recommend_coping_tool(request: CopingRequest, background_tasks: BackgroundTasks):
    try:
        tool_data = _suggest_tool(
            mood=request.mood,
            urge=request.urge,
            sleep_hours=request.sleep_hours,
            isolation=request.isolation,
            energy=request.energy,
            craving_type=request.craving_type,
        )
        risk = _risk_analyze(
            request.mood, request.urge, request.isolation, request.energy
        )
        anon_user_id = "anon-user"  # TODO: replace with your de-identified user id
        suggested_action = "Offer same-day check-in"

        if risk["score"] >= RISK_HIGH_THRESHOLD:
            queue_clinician_alert(
                background_tasks,
                user_id=anon_user_id,
                risk_score=risk["score"],
                factors=risk["factors"],
                suggested_action=suggested_action,
            )

        return CopingResponse(
            **tool_data,
            risk_score=risk["score"],
            risk_level=risk["level"],
            risk_factors=risk["factors"],
        )

    except Exception as e:
        logger.error(f"Coping tool failed | Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Coping tool generation failed",
        )


@router.get("/healthz")
def coping_health():
    return {"status": "ok", "service": "coping-engine"}
