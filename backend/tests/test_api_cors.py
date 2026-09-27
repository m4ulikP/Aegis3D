"""Focused test suite for FastAPI CORS middleware configuration."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client


def test_cors_allowed_origin_header(client: TestClient):
    """Verify requests from http://localhost:3000 receive Access-Control-Allow-Origin header."""
    headers = {"Origin": "http://localhost:3000"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_options_request(client: TestClient):
    """Verify OPTIONS preflight request from http://localhost:3000 succeeds with CORS headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/v1/zones", headers=headers)
    assert response.status_code in [200, 204]
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_unauthorized_origin_excluded(client: TestClient):
    """Verify requests from unlisted origin do not receive Access-Control-Allow-Origin header."""
    headers = {"Origin": "http://unauthorized-domain.com"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
