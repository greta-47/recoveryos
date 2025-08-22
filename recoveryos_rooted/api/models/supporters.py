from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Supporter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int
    email: str
    relationship: str = ""
    consent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
