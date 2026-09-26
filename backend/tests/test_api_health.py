import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client


def test_fastapi_app_import():
    """Verify FastAPI application can be imported and initialized."""
    assert app is not None
    assert app.title == "Aegis3D Backend API"


def test_get_health_liveness(client: TestClient):
    """Verify GET /health returns HTTP 200 and expected liveness JSON structure."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Aegis3D API"}


def test_get_health_db_readiness(client: TestClient):
    """Verify GET /health/db reaches real PostgreSQL and returns HTTP 200."""
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_get_health_db_unavailable_handling(client: TestClient):
    """Verify GET /health/db handles database error and returns HTTP 503 without exposing secrets."""
    def mock_broken_get_db():
        class FailingSession:
            def execute(self, statement):
                raise ConnectionError("Simulated database connection failure")
            def close(self):
                pass
        yield FailingSession()

    app.dependency_overrides[get_db] = mock_broken_get_db
    try:
        response = client.get("/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"] == {"status": "error", "database": "unreachable"}
    finally:
        app.dependency_overrides.clear()
