from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Checkin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    mood: int
    urge: int
    sleep_hours: float = 0
    isolation_score: int = 0
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
