import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.main import app
from app.database.seed import seed_products, seed_users


# ==========================================
# Register Models With SQLAlchemy Metadata
# ==========================================

from app.models.user import User  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.cart import Cart  # noqa: F401
from app.models.cart_item import CartItem  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.order_item import OrderItem  # noqa: F401
from app.models.payment import Payment  # noqa: F401


# ==========================================
# Test Database
# ==========================================

TEST_DATABASE_URL = "sqlite://"


test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def enable_sqlite_foreign_keys(
    dbapi_connection,
    _connection_record,
):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
    Create the test database tables before the
    test session and remove everything afterward.

    Individual test isolation is handled by the
    function-scoped db fixture below.
    """

    # ------------------------------------------
    # Create Tables
    # ------------------------------------------

    Base.metadata.create_all(
        bind=test_engine,
    )

    yield

    # ------------------------------------------
    # Clean Up Test Database
    # ------------------------------------------

    Base.metadata.drop_all(
        bind=test_engine,
    )


# ==========================================
# Database Session
# ==========================================

@pytest.fixture
def db() -> Session:
    """
    Provide a completely isolated database session
    for each test.

    The schema is recreated for every test so that
    records created by one test cannot affect another.
    """

    # ------------------------------------------
    # Reset Schema
    # ------------------------------------------

    Base.metadata.drop_all(
        bind=test_engine,
    )

    Base.metadata.create_all(
        bind=test_engine,
    )

    # ------------------------------------------
    # Create Session
    # ------------------------------------------

    session = TestingSessionLocal()

    try:
        # --------------------------------------
        # Seed Test Data
        # --------------------------------------

        seed_users(session)
        seed_products(session)

        session.commit()

        yield session

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


# ==========================================
# FastAPI Test Client
# ==========================================

@pytest.fixture
def client(db: Session):
    """
    Provide a FastAPI TestClient using the
    isolated test database session.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()