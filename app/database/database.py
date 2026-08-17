from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


# ==========================================
# Database Engine
# ==========================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)


# ==========================================
# Database Session
# ==========================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ==========================================
# Base Model
# ==========================================

Base = declarative_base()


# ==========================================
# Database Dependency
# ==========================================

def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for FastAPI requests.

    The session is automatically closed after
    the request is completed.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()