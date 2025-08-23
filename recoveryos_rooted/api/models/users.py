from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    role: str = "patient"
    locale: str = "en-CA"
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
