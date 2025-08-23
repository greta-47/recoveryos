from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel



class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    role: str = "patient"  # patient|supporter|clinician|admin
    locale: str = "en-CA"
    created_at: datetime = Field(default_factory=datetime.utcnow)
