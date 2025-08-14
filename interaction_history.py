from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class InteractionHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    interaction_type: str
    content: str
    ai_response: str = ""
    
    emotional_context: str = ""
    clinical_notes: str = ""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "interaction_type": "checkin",
                "content": "Feeling anxious today, urge level 4",
                "ai_response": "I hear that you're feeling anxious...",
                "emotional_context": "anxiety, high_urge",
                "clinical_notes": "elevated risk, suggested grounding"
            }
        }
