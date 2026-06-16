from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_system_status_endpoint() -> None:
    response = client.get("/api/system/status")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert body["success"] is True
    assert data["camera"]["status"] == "online"
    assert data["atlas"]["npuUsage"] == 38.4
    assert data["model"]["modelVersion"] == "detector-v1"
    assert data["dataFreshness"] == "fresh"


def test_dashboard_endpoint() -> None:
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert body["success"] is True
    assert data["pageState"] == "ready"
    assert data["deviceCount"] == 4
    assert data["latestHighRiskAlarm"]["riskLevel"] == "high"
