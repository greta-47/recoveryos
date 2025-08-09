from fastapi import FastAPI
from .db import init_db
from .routes import checkins, coping, supporters, risk, briefings, admin_clinician

app = FastAPI(title="RecoveryOS API", version="0.1.0")
init_db()

app.include_router(checkins.router)
app.include_router(coping.router)
app.include_router(supporters.router)
app.include_router(risk.router)
app.include_router(briefings.router)
app.include_router(admin_clinician.router)

@app.get("/")
def root():
    return {"ok": True, "service": "RecoveryOS"}
