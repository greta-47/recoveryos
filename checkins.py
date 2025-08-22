# checkins.py
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

# ======================
# PHI / PII heuristics
# ======================
_PHI_PATTERNS = [
    r"\b\d{3}-\d{3}-\d{4}\b",                              # phone (NA)
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", # email
    r"\bDOB[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",         # DOB
    r"\b(SIN|SSN)[:\s]*\d{3}[- ]?\d{3}[- ]?\d{3}\b",       # SIN/SSN
    r"\b\d{3}-\d{2}-\d{4}\b",                              # SSN (US style)
    r"\b[A-Z]{2}\d{6}\b",                                  # simple health card-ish
]
_PHI_RE = re.compile("|".join(_PHI_PATTERNS), re.I)


def _sanitize_notes(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    if _PHI_RE.search(text):
        # Redact the exact matches with [REDACTED]
        return _PHI_RE.sub("[REDACTED]", text)
    return text


def _validate_tz(tz: Optional[str]) -> Optional[str]:
    if tz is None or tz.strip() == "":
        return None
    try:
        # Will raise if invalid
        ZoneInfo(tz)
        return tz
    except Exception:
        raise ValueError("Invalid timezone. Use an IANA string like 'America/Vancouver'.")


# ======================
# Input Model: Patient Check-In
# ======================
class CheckinIn(BaseModel):
    """
    Daily check-in from patient.
    All fields are de-identified and voluntary.
    """
    mood: int = Field(
        ...,
        ge=1,
        le=5,
        description="Mood level: 1 (struggling) to 5 (strong)",
    )
    urge: int = Field(
        ...,
        ge=1,
        le=5,
        description="Urge to use: 1 (low) to 5 (high)",
    )
    sleep_hours: float = Field(
        0,
        ge=0,
        le=24,
        description="Hours slept last night",
    )
    isolation_score: int = Field(
        0,
        ge=0,
        le=5,
        description="Social connection: 0 (isolated) to 5 (connected)",
    )
    # FIX: default must meet constraints (ge=1). Use neutral midpoint = 3.
    energy_level: int = Field(
        3,
        ge=1,
        le=5,
        description="Energy level: 1 (exhausted) to 5 (energized)",
    )
    craving_type: Optional[Literal["opioid", "alcohol", "stimulant", "benzo", "other"]] = Field(
        None,
        description="Type of substance the urge is for (if known)",
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Free-text notes (avoid PHI: no names, locations, dates)",
    )
    timezone: Optional[str] = Field(
        None,
        description="IANA timezone (e.g., America/Vancouver) for time context",
    )

    # Pydantic v2 config
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mood": 3,
                    "urge": 4,
                    "sleep_hours": 6.5,
                    "isolation_score": 2,
                    "energy_level": 2,
                    "craving_type": "opioid",
                    "notes": "Felt shaky after work. Used grounding.",
                    "timezone": "America/Vancouver",
                }
            ]
        }
    }

    # ---- Validators (Pydantic v2) ----
    @field_validator("notes")
    @classmethod
    def _no_phi_in_notes(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_notes(v)

    @field_validator("timezone")
    @classmethod
    def _tz_valid(cls, v: Optional[str]) -> Optional[str]:
        return _validate_tz(v)


# ======================
# Output Model: AI Suggestion
# ======================
class SuggestionOut(BaseModel):
    """
    AI-generated support response.
    Must be trauma-informed, non-shaming, and actionable.
    """
    message: str = Field(..., description="Personalized encouragement or acknowledgment")
    tool: str = Field(..., description="Coping skill or resource (e.g., 'Box breathing 4x4')")
    category: Literal["grounding", "breathing", "distraction", "connection", "professional-help"] = Field(
        ..., description="Type of coping strategy"
    )
    urgency_level: Literal["low", "moderate", "high"] = Field(
        "low", description="Urgency based on inputs (for routing)"
    )
    follow_up_suggestion: Optional[str] = Field(
        None, description="Next step (e.g., 'Text your sponsor')"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="UTC timestamp of response",
    )


# ======================
# Optional: Internal Analytics Model
# ======================
class CheckinAnalytics(BaseModel):
    """
    De-identified model for trend detection and AI insights.
    Used internally — never includes PHI.
    """
    user_id: str  # Anonymized ID (e.g., "usr-abc123")
    date: str  # YYYY-MM-DD
    mood: int
    urge: int
    sleep_hours: float
    isolation_score: int
    energy_level: int
    craving_type: Optional[str]
    engagement_flag: Literal["high", "medium", "low"]
    risk_score: float = Field(ge=0, le=10)
    ai_notes: Optional[str] = None  # e.g., "Urge rising for 3 days"


# ======================
# Helpers: Suggestion & Analytics
# ======================
def suggest_from_checkin(ci: CheckinIn) -> SuggestionOut:
    """
    Deterministic, trauma-informed suggestion based on simple rules.
    Mirrors the logic used in main.py but centralizes it here.
    """
    # Urgency heuristic
    high = ci.urge >= 4 or ci.mood <= 2
    moderate = (not high) and (ci.sleep_hours < 5 or ci.isolation_score <= 1 or ci.energy_level <= 2)
    urgency = "high" if high else "moderate" if moderate else "low"

    # Tool & category
    if ci.urge >= 4:
        tool = "Urge Surfing — 5-minute guided wave visualization"
        category = "grounding"
        msg = "Thanks for checking in. Strong urges can feel intense and temporary. Let’s ride the wave together."
        follow = "If the urge stays high after 10 minutes, message your support person or use a craving-delay timer."
    elif ci.mood <= 2:
        tool = "5-4-3-2-1 Grounding"
        category = "grounding"
        msg = "You’re not alone—low mood happens. Try this short grounding practice to steady your body first."
        follow = "After grounding, consider a brief walk or light stretch to shift state."
    elif ci.sleep_hours < 5:
        tool = "Body Scan (10 min) + Wind-Down Routine"
        category = "breathing"
        msg = "Sleep debt can amplify urges. A brief body scan can calm your system before bed."
        follow = "Aim for a consistent bedtime and dim lights 60 minutes earlier tonight."
    elif ci.isolation_score <= 1:
        tool = "Connection Micro-task (2 min)"
        category = "connection"
        msg = "Connection helps recovery. A quick check-in with a safe person can lower urges."
        follow = "Send a two-line text to someone supportive: share one win and one thing you’re trying."
    else:
        tool = "Box Breathing 4×4 (2 min)"
        category = "breathing"
        msg = "Nice work staying engaged today. A short breath reset can keep momentum going."
        follow = "Log one helpful action you’ll repeat tomorrow."

    return SuggestionOut(
        message=msg,
        tool=tool,
        category=category,  # type: ignore[arg-type]
        urgency_level=urgency,  # type: ignore[arg-type]
        follow_up_suggestion=follow,
    )


def analytics_from_checkin(ci: CheckinIn, user_id: str, date: Optional[str] = None) -> CheckinAnalytics:
    """
    Convert a CheckinIn to a CheckinAnalytics record with a simple risk score.
    Risk score (0–10) is a weighted combination of risk factors.
    """
    # Normalize to 0..1 then weight
    urge_risk = (ci.urge - 1) / 4  # 0..1
    mood_risk = (5 - ci.mood) / 4  # 0..1 (lower mood = higher risk)
    sleep_risk = 1.0 if ci.sleep_hours < 5 else 0.0
    iso_risk = 1.0 if ci.isolation_score <= 1 else 0.0
    energy_risk = 1.0 if ci.energy_level <= 2 else 0.0

    # Weights (sum to 1.0 conceptually, then scale to 10)
    score_0_1 = (
        urge_risk * 0.55 +
        mood_risk * 0.20 +
        sleep_risk * 0.10 +
        iso_risk * 0.10 +
        energy_risk * 0.05
    )
    score = round(min(max(score_0_1 * 10, 0.0), 10.0), 2)

    engagement_flag: Literal["high", "medium", "low"]
    if ci.notes and len(ci.notes.strip()) >= 40:
        engagement_flag = "high"
    elif ci.notes:
        engagement_flag = "medium"
    else:
        engagement_flag = "low"

    return CheckinAnalytics(
        user_id=user_id,
        date=(date or datetime.utcnow().date().isoformat()),
        mood=ci.mood,
        urge=ci.urge,
        sleep_hours=ci.sleep_hours,
        isolation_score=ci.isolation_score,
        energy_level=ci.energy_level,
        craving_type=ci.craving_type,
        engagement_flag=engagement_flag,
        risk_score=score,
        ai_notes=None,
    )


__all__ = [
    "CheckinIn",
    "SuggestionOut",
    "CheckinAnalytics",
    "suggest_from_checkin",
    "analytics_from_checkin",
]
