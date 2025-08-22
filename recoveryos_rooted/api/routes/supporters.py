from fastapi import APIRouter
from pydantic import BaseModel


class ConsentIn(BaseModel):
    consent: bool
router = APIRouter(prefix="/supporters", tags=["supporters"])
@router.post("/consent")
def set_consent(body: ConsentIn):
    return {"ok": True, "consent": body.consent}
