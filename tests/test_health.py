from sqlalchemy.exc import OperationalError

from app.database.database import get_db
from app.main import app


# ==========================================
# Health Check
# ==========================================

def test_health_check_reports_database_connected(client):
    """
    A healthy service answers 200 and says so explicitly.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_health_check_reports_unhealthy_without_database(
    client,
):
    """
    A health check that only proves the process is alive
    keeps a broken instance in the load balancer. When the
    database is unreachable the endpoint must answer 503 so
    the instance is taken out of rotation.
    """

    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError(
                "SELECT 1",
                {},
                Exception("connection refused"),
            )

    def override_get_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "database": "unavailable",
    }


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
