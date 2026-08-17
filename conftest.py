import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.database import Base, get_db
from app.main import app

# Make sure all models are registered with Base.metadata
from app.models.user import User  # noqa: F401


# ==========================================
# Test Database
# ==========================================

TEST_DATABASE_URL = (
    "postgresql://postgres:hangouts100"
    "@localhost:5432/ultimatekits_test"
)


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


# ==========================================
# Test Database Setup
# ==========================================

@pytest.fixture(
    scope="session",
    autouse=True,
)
def setup_test_database():
    """
    Create all test database tables before the
    test session and remove them afterward.
    """

    Base.metadata.create_all(
        bind=test_engine,
    )

    yield

    Base.metadata.drop_all(
        bind=test_engine,
    )


# ==========================================
# Database Session
# ==========================================

@pytest.fixture
def db() -> Session:
    """
    Provide a database session for each test.
    """

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()


# ==========================================
# FastAPI Test Client
# ==========================================

@pytest.fixture
def client(db: Session):
    """
    Provide a FastAPI TestClient using the
    test database session.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()