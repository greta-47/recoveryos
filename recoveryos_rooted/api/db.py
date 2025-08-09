from sqlmodel import SQLModel, create_engine, Session
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoveryos.db")
engine = create_engine(DATABASE_URL, echo=False)
def init_db():
    from .models import users, checkins, supporters, tools, risk_events  # noqa
    SQLModel.metadata.create_all(engine)
def get_session():
    return Session(engine)
