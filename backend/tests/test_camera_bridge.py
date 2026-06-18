from datetime import datetime, timezone
from pathlib import Path

from app.models.inspection import DetectionUploadRequest
from app.services.camera_bridge import (
    build_camera_payload,
    capture_candidates,
    format_frame_id,
    raw_frame_path,
    raw_frame_url,
)


def test_frame_paths_follow_upload_contract(tmp_path: Path) -> None:
    assert format_frame_id(1) == "frame-000001"
    assert raw_frame_url("inspection-20260618-0001", "frame-000001") == (
        "/uploads/raw/inspection-20260618-0001/frame-000001.jpg"
    )
    assert raw_frame_path(tmp_path, "inspection-20260618-0001", "frame-000001") == (
        tmp_path / "raw" / "inspection-20260618-0001" / "frame-000001.jpg"
    )


def test_payload_uses_existing_detection_upload_contract() -> None:
    payload = build_camera_payload(
        inspection_id="inspection-20260618-0001",
        frame_id="frame-000001",
        frame_seq=1,
        timestamp=datetime(2026, 6, 18, 22, 0, tzinfo=timezone.utc),
        device_id="device-001",
        image_url="/uploads/raw/inspection-20260618-0001/frame-000001.jpg",
        image_width=640,
        image_height=480,
        latency_ms=12.34,
        fps=1.2,
        cpu_usage=10,
        memory_usage=20,
    )

    assert isinstance(payload, DetectionUploadRequest)
    assert payload.idempotencyKey == "inspection-20260618-0001:frame-000001"
    assert payload.uploadReason == "periodic_sample"
    assert payload.detections == []
    assert payload.annotatedImageUrl is None
    assert payload.performance.npuUsage is None


def test_capture_candidates_reuse_working_backend() -> None:
    assert capture_candidates("auto") == ["ffmpeg", "v4l2"]
    assert capture_candidates("auto", preferred_backend="ffmpeg") == ["ffmpeg", "v4l2"]
    assert capture_candidates("v4l2") == ["v4l2"]
