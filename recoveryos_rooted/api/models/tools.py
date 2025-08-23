from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Tool(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    category: str = Field(index=True)
    content: str
    tags: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
