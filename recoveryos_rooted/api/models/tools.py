from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
class Tool(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    content: str
    tags: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
