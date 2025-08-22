# db/db.py
import logging
import os
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

# ----------------------
# Logging
# ----------------------
logger = logging.getLogger("recoveryos")

# ----------------------
# Database URL
# ----------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Only allow SQLite in dev
    if os.getenv("ENV", "development") == "production":
        raise RuntimeError("DATABASE_URL is required in production")
    DATABASE_URL = "sqlite:///./recoveryos.db"
    logger.warning("Using SQLite in dev mode — not for production")

# Detect DB type for tuning
is_sqlite = DATABASE_URL.startswith("sqlite")
is_postgres = DATABASE_URL.startswith("postgresql")


# ----------------------
# Engine Configuration
# ----------------------
def create_db_engine():
    """Create engine with production-safe defaults."""
    connect_args = {}
    engine_kwargs = {}

    if is_sqlite:
        connect_args["check_same_thread"] = False  # Required for async
        engine_kwargs["echo"] = False  # Set to True only in dev
    elif is_postgres:
        # Connection pooling for production
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_pre_ping"] = True  # Handle dropped connections
        engine_kwargs["echo"] = False

    return create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)


engine = create_db_engine()


# ----------------------
# Initialize DB
# ----------------------
def init_db():
    """
    Create all tables.
    Call once at startup.
    """
    from .models import Checkin, ConsentRecord, RiskEvent, Supporter, Tool, User  # noqa

    SQLModel.metadata.create_all(engine)
    logger.info("✅ Database initialized — all tables created or verified")


# ----------------------
# Session Management
# ----------------------
@contextmanager
def get_session():
    """
    Thread-safe session context manager.
    Use in routes with: `with get_session() as session:`
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session failed | Error: {str(e)}")
        raise
    finally:
        session.close()


# Optional: FastAPI dependency (if using)
# def get_db():
#     with get_session() as session:
#         yield session
