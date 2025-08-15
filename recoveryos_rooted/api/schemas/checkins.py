from pydantic import BaseModel, Field
from typing import Optional


class CheckinIn(BaseModel):
    mood: int = Field(ge=1, le=5)
    urge: int = Field(ge=1, le=5)
    sleep_hours: float = 0
    isolation_score: int = 0
    notes: Optional[str] = ""


class SuggestionOut(BaseModel):
    message: str
    tool: str
