from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "online"
    assert body["data"]["version"] == "0.1.0"
    assert body["message"] == "ok"
    assert "timestamp" in body
