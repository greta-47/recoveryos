from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CheckinIn(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1–5")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1–5")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="0–5 social connection")
    notes: Optional[str] = Field("", max_length=500, description="Avoid PHI")


class SuggestionOut(BaseModel):
    message: str
    tool: str
