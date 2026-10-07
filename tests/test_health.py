# Allows for testing of the API without actually starting a server
from fastapi.testclient import TestClient

from app.main import app

# The "Fake" browser/API consumer talking to our app
client = TestClient(app)

# Runs all functions starting with "test_" and checks they all pass
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}