# coping.py
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict
from datetime import datetime
import os
import logging

from alerts import queue_clinician_alert  # <-- add this

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
    craving_type: Optional[Literal["alcohol", "opioid", "stimulant", "benzo", "other"]] = Field(
        None, description="Substance the urge is for (if known)"
    )
    context: Optional[str] = Field(None, max_length=200, description="Brief context (avoid PHI: no names, locations)")

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
                    "context": "After argument with partner"
                }
            ]
        }
    }

class CopingResponse(BaseModel):
    tool: str = Field(..., description="Name of the coping skill")
    description: str = Field(..., description="How to do it (1–2 sentences)")
    category: Literal["grounding", "breathing", "distraction", "connection", "body-scan", "professional-help", "mindfulness"] = Field(..., description="Type of tool")
    urgency_level: Literal["low", "moderate", "high"] = Field("moderate", description="For routing logic")
    suggested_duration: str = Field("5 minutes", description="Recommended time to spend")
    message: str = Field(..., description="Personalized encouragement")
    timestamp: str = Field(default_factory=lambda: f"{datetime.utcnow().isoformat()}Z", description="UTC timestamp")
    resources: List[str] = Field(default_factory=list, description="Optional: links to videos, audio, or handouts")

    # NEW (for UI + alerts)
    risk_score: float = Field(0.0, ge=0, le=10, description="0–10 composite risk score")
    risk_level: Literal["Low", "Moderate", "High", "Severe"] = Field("Low", description="Discrete risk level")
    risk_factors: List[Dict] = Field(default_factory=list, description="Top contributing factors")

router = APIRouter(prefix="/coping", tags=["coping"])

# ----------------------
# Tool Engine (simple rules, same as before)
# ----------------------
def get_coping_tool(mood: int, urge: int, sleep_hours: float, isolation: int, energy: int, craving_type: Optional[str] = None, context: Optional[str] = None) -> dict:
    base = {
        "tool": "Box Breathing",
        "description": "Inhale 4s, hold 4s, exhale 4s, hold 4s. Repeat.",
        "category": "breathing",
        "suggested_duration": "5 minutes",
        "message": "You’re not alone. This simple breath can help you reset.",
    }

    if urge >= 4:
        if craving_type == "opioid":
            base.update({
                "tool": "Urge Surfing",
                "description": "Visualize the urge as a wave. It rises, peaks, and falls. Ride it without acting.",
                "category": "grounding",
                "message": "This urge will pass. Surf it, don’t drown in it."
            })
        elif energy <= 2:
            base.update({
                "tool": "Progressive Muscle Relaxation",
                "description": "Tense and release each muscle group from toes to head.",
                "category": "body-scan",
                "message": "When exhaustion meets craving, this can help your body let go."
            })
        else:
            base.update({
                "tool": "5-4-3-2-1 Grounding",
                "description": "Name 5 you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.",
                "category": "grounding",
                "message": "You’re here. You’re safe. Use your senses to return to the present."
            })
    elif mood <= 2 and isolation <= 2:
        base.update({
            "tool": "Reach Out Script",
            "description": "Text: “I’m having a tough moment. Can I talk for 5 minutes?”",
            "category": "connection",
            "suggested_duration": "10 minutes",
            "message": "Connection is medicine. One sentence can shift the weight."
        })
    elif sleep_hours < 5:
        base.update({
            "tool": "Body Scan Meditation",
            "description": "Move attention from toes to head, noticing tension without judgment.",
            "category": "mindfulness",
            "suggested_duration": "10 minutes",
            "message": "When sleep feels far away, this can help your body relax enough to rest."
        })

    if urge >= 4:
        base["urgency_level"] = "high"
    elif mood <= 2 or isolation <= 2 or sleep_hours < 5:
        base["urgency_level"] = "moderate"
    else:
        base["urgency_level"] = "low"

    if base["category"] == "grounding":
        base.setdefault("resources", []).append("https://recoveryos.app/guided/urge-surfing.mp3")

    return base

# ----------------------
# Risk Scoring (0–10) + factorization
# ----------------------
def compute_risk(mood: int, urge: int, sleep_hours: float, isolation: int, energy: int, craving_type: Optional[str]) -> Dict:
    # Normalize 1..5 signals to 0..1 where higher = higher risk
    risk_urge = (urge - 1) / 4  # 0..1
    risk_mood = (5 - mood) / 4  # low mood = higher risk
    risk_iso = (3 - min(isolation, 3)) / 2 if isolation <= 3 else 0  # isolation 1..3 risky
    risk_sleep = 1.0 if sleep_hours < 4 else (0.5 if sleep_hours < 6 else 0.0)
    risk_energy = (3 - min(energy, 3)) / 2 if energy <= 3 else 0

    craving_bonus = 0.25 if craving_type in {"opioid", "stimulant"} else (0.1 if craving_type in {"alcohol", "benzo"} else 0.0)

    # Weighted sum -> 0..10
    score = 10 * (
        0.35 * risk_urge +
        0.20 * risk_mood +
        0.15 * risk_iso +
        0.15 * risk_sleep +
        0.10 * risk_energy +
        0.05 * craving_bonus
    )
    score = max(0.0, min(10.0, round(score, 1)))

    def level(s: float) -> str:
        if s >= 9: return "Severe"
        if s >= 7: return "High"
        if s >= 4: return "Moderate"
        return "Low"

    factors = []
    if urge >= 4:
        factors.append({"name": "High urge", "impact": 0.35, "explanation": f"Urge {urge}/5 in last check-in"})
    if mood <= 2:
        factors.append({"name": "Low mood", "impact": 0.20, "explanation": f"Mood {mood}/5"})
    if isolation <= 2:
        factors.append({"name": "Isolation", "impact": 0.15, "explanation": f"Isolation {isolation}/5"})
    if sleep_hours < 6:
        factors.append({"name": "Poor sleep", "impact": 0.15, "explanation": f"Sleep {sleep_hours}h"})
    if energy <= 2:
        factors.append({"name": "Low energy", "impact": 0.10, "explanation": f"Energy {energy}/5"})
    if craving_bonus > 0:
        factors.append({"name": "Craving type", "impact": 0.05, "explanation": f"{craving_type} increases risk"})

    return {"score": score, "level": level(score), "factors": factors}

# ----------------------
# Routes
# ----------------------
@router.post("/recommend", response_model=CopingResponse)
def recommend_coping_tool(request: CopingRequest, background_tasks: BackgroundTasks):
    """
    Get a personalized, trauma-informed coping tool.
    Also returns a de-identified risk score/factors and queues Slack alert if risk is high.
    """
    logger.info(f"Coping tool requested | Urge={request.urge}, Mood={request.mood}")

    try:
        tool_data = get_coping_tool(
            mood=request.mood,
            urge=request.urge,
            sleep_hours=request.sleep_hours,
            isolation=request.isolation,
            energy=request.energy,
            craving_type=request.craving_type,
            context=request.context
        )

        # Compute risk + maybe alert
        risk = compute_risk(
            mood=request.mood,
            urge=request.urge,
            sleep_hours=request.sleep_hours,
            isolation=request.isolation,
            energy=request.energy,
            craving_type=request.craving_type
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

        logger.info("Coping tool delivered | Tool='%s' | Urgency=%s | Risk=%.1f",
                    tool_data["tool"], tool_data["urgency_level"], risk["score"])

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
            detail="Coping tool generation failed"
        )

@router.get("/healthz")
def coping_health():
    return {"status": "ok", "service": "coping-engine"}
