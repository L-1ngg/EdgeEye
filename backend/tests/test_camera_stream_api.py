from fastapi.testclient import TestClient

from app.main import app
from app.services.camera_bridge import camera_bridge_service

client = TestClient(app)


def test_camera_stream_returns_mjpeg(monkeypatch) -> None:
    def fake_stream():
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg\r\n"

    monkeypatch.setattr(camera_bridge_service, "ensure_stream_available", lambda: None)
    monkeypatch.setattr(camera_bridge_service, "iter_mjpeg_stream", fake_stream)

    response = client.get("/api/camera/stream.mjpg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"Content-Type: image/jpeg" in response.content


def test_camera_stream_unavailable_returns_503() -> None:
    response = client.get("/api/camera/stream.mjpg")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CAMERA_STREAM_UNAVAILABLE"
