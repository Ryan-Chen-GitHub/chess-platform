from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_allows_dev_frontend():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_ignores_other_origins():
    response = client.get("/health", headers={"Origin": "http://other.example"})
    assert "access-control-allow-origin" not in response.headers