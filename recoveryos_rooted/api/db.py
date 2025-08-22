import os

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoveryos.db")
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    from .models import checkins, risk_events, supporters, tools, users  # noqa

    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)
