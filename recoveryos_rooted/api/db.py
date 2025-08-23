# db/__init__.py (or the file you’re editing)
import os
from sqlmodel import Session, SQLModel, create_engine

# Database URL (defaults to local SQLite for dev)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoveryos.db")
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """
    Import models so SQLModel.metadata is populated, then create tables.
    Works whether your models are defined as classes or split into modules.
    """
    # Try class-based model imports first
    try:
        from .models import Checkin, ConsentRecord, RiskEvent, Supporter, Tool, User  # noqa: F401
    except Exception:
        # Fallback to module imports (side-effect: registers tables)
        try:
            from .models import checkins, risk_events, supporters, tools, users  # noqa: F401
        except Exception:
            # If neither style exists, proceed; create_all will just be a no-op
            pass

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
