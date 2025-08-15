from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Supporter(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int
    email: str
    relationship: str = ""
    consent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
