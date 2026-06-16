import json
from copy import deepcopy

from fastapi.testclient import TestClient

from app.services import inspection_service as service_module
from app.main import app
from app.services.inspection_service import current_timestamp


client = TestClient(app)


def detection_payload(inspection_id: str) -> dict:
    return {
        "idempotencyKey": f"{inspection_id}:frame-000001",
        "inspectionId": inspection_id,
        "frameId": "frame-000001",
        "frameSeq": 1,
        "timestamp": current_timestamp().isoformat(),
        "deviceId": "device-001",
        "isKeyFrame": True,
        "uploadReason": "fault_started",
        "imageUrl": "/uploads/raw/inspection/frame-000001.jpg",
        "annotatedImageUrl": "/uploads/annotated/inspection/frame-000001.jpg",
        "imageWidth": 1280,
        "imageHeight": 720,
        "detections": [
            {
                "category": "insulator_defect",
                "deviceType": "insulator",
                "faultType": "surface_damage",
                "confidence": 0.91,
                "bbox": [120, 80, 360, 420],
            }
        ],
        "performance": {
            "latencyMs": 42,
            "fps": 18.5,
            "cpuUsage": 42.5,
            "memoryUsage": 61.2,
            "npuUsage": 38.4,
        },
    }


def start_inspection() -> str:
    response = client.post(
        "/api/inspection/start",
        json={"deviceId": "device-001", "operator": "team", "source": "atlas"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "running"
    return body["data"]["inspectionId"]


def test_member4_detection_advice_and_report_flow() -> None:
    inspection_id = start_inspection()
    payload = detection_payload(inspection_id)

    upload = client.post("/api/detection/results", json=payload)
    assert upload.status_code == 200
    upload_data = upload.json()["data"]
    assert upload_data["accepted"] is True
    assert upload_data["duplicate"] is False
    assert upload_data["faultsCreated"] == 1
    assert upload_data["alarmsCreated"] == 1

    duplicate = client.post("/api/detection/results", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["duplicate"] is True

    latest = client.get(f"/api/inspections/{inspection_id}/latest-result")
    assert latest.status_code == 200
    latest_data = latest.json()["data"]
    assert latest_data["resultStatus"] == "ready"
    assert latest_data["faults"][0]["riskLevel"] == "high"

    devices = client.get("/api/devices")
    assert devices.status_code == 200
    assert devices.json()["data"]["total"] == 4

    inspections = client.get("/api/inspections")
    assert inspections.status_code == 200
    assert inspections.json()["data"]["items"][0]["faultCount"] == 1

    faults = client.get("/api/faults")
    assert faults.status_code == 200
    fault = faults.json()["data"]["items"][0]
    assert fault["faultType"] == "surface_damage"
    assert fault["occurrenceCount"] == 1

    alarms = client.get("/api/alarms")
    assert alarms.status_code == 200
    alarm = alarms.json()["data"]["items"][0]
    assert alarm["alarmLevel"] == "warning"

    events = client.get("/api/events")
    assert events.status_code == 200
    assert events.json()["data"]["items"][0]["adviceStatus"] == "none"

    patched = client.patch(
        f"/api/faults/{fault['faultId']}/status",
        json={"processStatus": "processing", "operator": "team", "note": "reviewing"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["processStatus"] == "processing"

    advice = client.post("/api/advice/generate", json={"faultId": fault["faultId"]})
    assert advice.status_code == 200
    advice_data = advice.json()["data"]
    assert advice_data["adviceStatus"] == "fallback"
    assert advice_data["modelName"] == "rule-template"

    saved_advice = client.get(f"/api/faults/{fault['faultId']}/advice")
    assert saved_advice.status_code == 200
    assert saved_advice.json()["data"]["adviceId"] == advice_data["adviceId"]

    finish = client.post(f"/api/inspections/{inspection_id}/finish", json={})
    assert finish.status_code == 200
    assert finish.json()["data"]["status"] == "completed"

    reports = client.get("/api/reports")
    assert reports.status_code == 200
    report = reports.json()["data"]["items"][0]
    assert report["reportStatus"] == "ready"

    detail = client.get(f"/api/reports/{report['reportId']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["advices"][0]["adviceId"] == advice_data["adviceId"]

    exported = client.get(f"/api/reports/{report['reportId']}/export?format=pdf")
    assert exported.status_code == 200
    assert exported.json()["data"]["downloadUrl"].endswith(".pdf")

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    dashboard_data = dashboard.json()["data"]
    assert dashboard_data["faultCount"] == 1
    assert dashboard_data["latestHighRiskAlarm"]["riskLevel"] == "high"

    system = client.get("/api/system/status")
    assert system.status_code == 200
    assert system.json()["data"]["model"]["latencyMs"] == 42


def test_detection_upload_idempotency_conflict() -> None:
    inspection_id = start_inspection()
    payload = detection_payload(inspection_id)
    assert client.post("/api/detection/results", json=payload).status_code == 200

    conflict_payload = deepcopy(payload)
    conflict_payload["imageUrl"] = "/uploads/raw/inspection/changed.jpg"
    conflict = client.post("/api/detection/results", json=conflict_payload)

    assert conflict.status_code == 409
    body = conflict.json()
    assert body["success"] is False
    assert body["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_advice_generation_uses_configured_llm_provider(monkeypatch) -> None:
    inspection_id = start_inspection()
    assert client.post("/api/detection/results", json=detection_payload(inspection_id)).status_code == 200
    fault_id = client.get("/api/faults").json()["data"]["items"][0]["faultId"]
    advice_content = {
        "possibleCauses": ["loose fitting"],
        "riskAnalysis": "Provider generated risk analysis.",
        "inspectionSteps": ["Check the fitting torque."],
        "maintenanceSuggestions": ["Tighten or replace the affected component."],
        "safetyNotes": ["Review the advice before field work."],
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(advice_content)}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        assert timeout == 1.5
        assert request.full_url == "https://llm.example.test/v1/chat/completions"
        return FakeResponse()

    monkeypatch.setattr(service_module.settings, "llm_provider", "openai-compatible")
    monkeypatch.setattr(service_module.settings, "llm_api_url", "https://llm.example.test/v1/chat/completions")
    monkeypatch.setattr(service_module.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(service_module.settings, "llm_model_name", "repair-model")
    monkeypatch.setattr(service_module.settings, "llm_timeout_seconds", 1.5)
    monkeypatch.setattr(service_module.settings, "llm_max_retries", 1)
    monkeypatch.setattr(service_module.urllib.request, "urlopen", fake_urlopen)

    response = client.post("/api/advice/generate", json={"faultId": fault_id})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["adviceStatus"] == "ready"
    assert data["modelName"] == "repair-model"
    assert data["possibleCauses"] == ["loose fitting"]
