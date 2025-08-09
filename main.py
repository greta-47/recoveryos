from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="RecoveryOS API", version="0.1.0")

class Checkin(BaseModel):
    mood: int = Field(ge=1, le=5)
    urge: int = Field(ge=1, le=5)
    sleep_hours: float = 0
    isolation_score: int = 0

@app.get("/")
def root():
    return {"ok": True, "service": "RecoveryOS"}

@app.post("/checkins")
def create_checkin(checkin: Checkin):
    tool = "Urge Surfing — 5-minute guided wave visualization" if checkin.urge >= 4 else "Breathing — Box breathing 4x4"
    return {"message": "Check-in received", "tool": tool, "data": checkin.dict()}
