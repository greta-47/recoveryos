from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import json


class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    communication_style: str = "supportive"
    triggers: str = ""
    coping_preferences: str = ""
    recovery_goals: str = ""
    voice_characteristics: str = ""

    personality_data: str = ""
    preferences_data: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_personality(self) -> Dict[str, Any]:
        if not self.personality_data:
            return {}
        try:
            return json.loads(self.personality_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_personality(self, data: Dict[str, Any]):
        self.personality_data = json.dumps(data)
        self.updated_at = datetime.utcnow()

    def get_preferences(self) -> Dict[str, Any]:
        if not self.preferences_data:
            return {}
        try:
            return json.loads(self.preferences_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_preferences(self, data: Dict[str, Any]):
        self.preferences_data = json.dumps(data)
        self.updated_at = datetime.utcnow()
