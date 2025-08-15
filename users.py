from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    role: str = "patient"  # patient|supporter|clinician|admin
    locale: str = "en-CA"
    created_at: datetime = Field(default_factory=datetime.utcnow)
