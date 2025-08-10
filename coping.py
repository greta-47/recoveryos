# coping.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
import logging

# ----------------------
# Logging
# ----------------------
logger = logging.getLogger("recoveryos")

# ----------------------
# Models
# ----------------------
class CopingRequest(BaseModel):
    """
    Input for coping tool recommendation.
    All fields are optional with safe defaults.
    """
    mood: int = Field(3, ge=1, le=5, description="1=struggling, 5=strong")
    urge: int = Field(3, ge=1, le=5, description="1=low, 5=high")
    sleep_hours: float = Field(7.0, ge=0, le=24, description="Hours slept last night")
    isolation: int = Field(3, ge=1, le=5, description="1=isolated, 5=connected")
    energy: int = Field(3, ge=1, le=5, description="1=exhausted, 5=energized")
    craving_type: Optional[Literal["alcohol", "opioid", "stimulant", "benzo", "other"]] = Field(
        None, description="Substance the urge is for (if known)"
    )
    context: Optional[str] = Field(
        None, max_length=200, description="Brief context (avoid PHI: no names, locations)"
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
    """
    Trauma-informed, actionable coping support.
    Designed to be used in apps, SMS, or clinician dashboards.
    """
    tool: str = Field(..., description="Name of the coping skill")
    description: str = Field(..., description="How to do it (1–2 sentences)")
    # Include both "mindfulness" and "body-scan" so rules below are valid
    category: Literal[
        "grounding", "breathing", "distraction", "connection", "mindfulness", "body-scan", "professional-help"
    ] = Field(..., description="Type of tool")
    urgency_level: Literal["low", "moderate", "high"] = Field("moderate", description="For routing logic")
    suggested_duration: str = Field("5 minutes", description="Recommended time to spend")
    message: str = Field(..., description="Personalized encouragement")
    timestamp: str = Field(
        default_factory=lambda: f"{datetime.utcnow().isoformat()}Z", description="UTC timestamp"
    )
    resources: List[str] = Field(default_factory=list, description="Optional links to audio/video/handouts")

# ----------------------
# Router
# ----------------------
router = APIRouter(prefix="/coping", tags=["coping"])

# ----------------------
# Coping Engine (Replace with AI or DB later)
# ----------------------
def get_coping_tool(
    mood: int,
    urge: int,
    sleep_hours: float,
    isolation: int,
    energy: int,
    craving_type: Optional[str] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic, trauma-informed rules that yield a coping tool.
    Safe defaults; no PHI is logged or returned.
    """
    # Default fallback
    base: Dict[str, Any] = {
        "tool": "Box Breathing 4×4",
        "description": "Inhale 4s, hold 4s, exhale 4s, hold 4s. Repeat for 5 minutes.",
        "category": "breathing",
        "suggested_duration": "5 minutes",
        "message": "You’re not alone. A short breathing reset can help your body settle.",
    }

    # High urge (4–5) → prioritize urge regulation & grounding
    if urge >= 4:
        if (craving_type or "").lower() == "opioid":
            base.update(
                tool="Urge Surfing",
                description="Notice the craving like a wave—rising, peaking, falling—without acting on it.",
                category="grounding",
                suggested_duration="5–7 minutes",
                message="Cravings pass. Ride the wave; you don’t have to do anything but breathe.",
            )
        elif energy <= 2:
            base.update(
                tool="Progressive Muscle Relaxation",
                description="Tense then release each muscle group from toes to head to discharge tension.",
                category="body-scan",
                suggested_duration="6–8 minutes",
                message="When exhaustion and urges collide, a body reset can help your nervous system settle.",
            )
        else:
            base.update(
                tool="5-4-3-2-1 Grounding",
                description="Name 5 things you see, 4 feel, 3 hear, 2 smell, 1 taste to return to the present.",
                category="grounding",
                suggested_duration="5 minutes",
                message="Let’s anchor in the here-and-now. You’re safe, and this moment will move.",
            )

    # Low mood + isolation → connection task
    elif mood <= 2 and isolation <= 2:
        base.update(
            tool="Reach-Out Script",
            description="Text a trusted person: “I’m having a tough moment. Do you have 5 minutes to chat?”",
            category="connection",
            suggested_duration="10 minutes",
            message="Connection is medicine. One short message can shift how this feels.",
        )

    # Sleep debt → body/mind relaxation
    elif sleep_hours < 5:
        base.update(
            tool="Body Scan Meditation",
            description="Sweep attention from toes to head, noticing tension without judgment.",
            category="mindfulness",
            suggested_duration="10 minutes",
            message="Sleep debt can amplify urges. A brief scan can calm your system for rest.",
        )

    # Set urgency level
    if urge >= 4:
        base["urgency_level"] = "high"
    elif mood <= 2 or isolation <= 2 or sleep_hours < 5:
        base["urgency_level"] = "moderate"
    else:
        base["urgency_level"] = "low"

    # Optional resources by category (URLs are placeholders; replace with your CDN)
    resources_by_category = {
        "grounding": ["https://recoveryos.app/guided/urge-surfing.mp3"],
        "breathing": ["https://recoveryos.app/guided/box-breathing.mp3"],
        "mindfulness": ["https://recoveryos.app/guided/body-scan.mp3"],
        "body-scan": ["https://recoveryos.app/guided/pmr.mp3"],
    }
    base["resources"] = resources_by_category.get(base["category"], [])

    return base

# ----------------------
# Routes
# ----------------------
@router.post("/recommend", response_model=CopingResponse)
def recommend_coping_tool(request: CopingRequest, background_tasks: BackgroundTasks) -> CopingResponse:
    """
    Get a personalized, trauma-informed coping tool.
    Used in daily check-ins, crisis moments, and peer support.
    """
    try:
        tool_data = get_coping_tool(
            mood=request.mood,
            urge=request.urge,
            sleep_hours=request.sleep_hours,
            isolation=request.isolation,
            energy=request.energy,
            craving_type=request.craving_type,
            context=request.context,
        )

        # Log anonymized decision (no PHI)
        background_tasks.add_task(
            logger.info,
            f"Coping tool delivered | Urge={request.urge} Mood={request.mood} "
            f"Tool='{tool_data['tool']}' Urgency={tool_data['urgency_level']}",
        )

        return CopingResponse(**tool_data)

    except Exception as e:
        logger.error(f"Coping tool failed | Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Coping tool generation failed",
        )

# ----------------------
# Health Check
# ----------------------
@router.get("/healthz")
def coping_health():
    return {"status": "ok", "service": "coping-engine"}
