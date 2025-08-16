from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class RiskEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    score: float
    factors: str  # json stringified
    created_at: datetime = Field(default_factory=datetime.utcnow)
