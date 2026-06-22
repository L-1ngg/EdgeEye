import threading
from datetime import datetime, timezone
from pathlib import Path

from app.models.inspection import Detection, DetectionUploadRequest
from app.services.camera_bridge import (
    CameraBridgeService,
    SystemStats,
    annotated_frame_path,
    annotated_frame_url,
    build_camera_payload,
    capture_candidates,
    extract_jpeg_frames,
    format_frame_id,
    mjpeg_part,
    prune_raw_frames,
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


def test_payload_accepts_model_detections_and_annotated_url() -> None:
    detection = Detection(
        category="insulator_surface_damage",
        deviceType="insulator",
        faultType="surface_damage",
        confidence=0.82,
        bbox=(10, 20, 120, 220),
    )

    payload = build_camera_payload(
        inspection_id="inspection-20260618-0001",
        frame_id="frame-000002",
        frame_seq=2,
        timestamp=datetime(2026, 6, 18, 22, 0, tzinfo=timezone.utc),
        device_id="device-001",
        image_url="/uploads/raw/inspection-20260618-0001/frame-000002.jpg",
        annotated_image_url="/uploads/annotated/inspection-20260618-0001/frame-000002.jpg",
        image_width=640,
        image_height=480,
        detections=[detection],
        latency_ms=28.5,
        fps=15,
        cpu_usage=10,
        memory_usage=20,
    )

    assert payload.annotatedImageUrl == "/uploads/annotated/inspection-20260618-0001/frame-000002.jpg"
    assert len(payload.detections) == 1
    assert payload.detections[0].faultType == "surface_damage"
    assert payload.detections[0].imageWidth == 640
    assert payload.performance.latencyMs == 28.5


def test_annotated_frame_paths_follow_upload_contract(tmp_path: Path) -> None:
    assert annotated_frame_url("inspection-20260618-0001", "frame-000001") == (
        "/uploads/annotated/inspection-20260618-0001/frame-000001.jpg"
    )
    assert annotated_frame_path(tmp_path, "inspection-20260618-0001", "frame-000001") == (
        tmp_path / "annotated" / "inspection-20260618-0001" / "frame-000001.jpg"
    )


def test_capture_candidates_reuse_working_backend() -> None:
    assert capture_candidates("auto") == ["ffmpeg", "v4l2"]
    assert capture_candidates("auto", preferred_backend="ffmpeg") == ["ffmpeg", "v4l2"]
    assert capture_candidates("v4l2") == ["v4l2"]


def test_mjpeg_part_wraps_jpeg_content() -> None:
    frame = b"\xff\xd8image-bytes\xff\xd9"
    part = mjpeg_part(frame)

    assert part.startswith(b"--frame\r\n")
    assert b"Content-Type: image/jpeg\r\n" in part
    assert f"Content-Length: {len(frame)}".encode("ascii") in part
    assert part.endswith(frame + b"\r\n")


def test_extract_jpeg_frames_across_chunks() -> None:
    buffer = bytearray()
    first = list(extract_jpeg_frames(buffer, b"noise\xff\xd8one"))
    second = list(extract_jpeg_frames(buffer, b"\xff\xd9gap\xff\xd8two\xff\xd9tail"))

    assert first == []
    assert second == [b"\xff\xd8one\xff\xd9", b"\xff\xd8two\xff\xd9"]


def test_prune_raw_frames_keeps_newest_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "inspection-20260618-0001"
    raw_dir.mkdir(parents=True)
    for index in range(4):
        frame = raw_dir / f"frame-00000{index + 1}.jpg"
        frame.write_bytes(b"frame")

    deleted = prune_raw_frames(
        uploads_dir=tmp_path,
        inspection_id="inspection-20260618-0001",
        keep_count=2,
    )

    assert [path.name for path in deleted] == ["frame-000001.jpg", "frame-000002.jpg"]
    assert sorted(path.name for path in raw_dir.glob("*.jpg")) == ["frame-000003.jpg", "frame-000004.jpg"]


def test_sample_scheduler_skips_when_previous_sample_is_still_running() -> None:
    service = CameraBridgeService()
    started = threading.Event()
    release = threading.Event()
    calls: list[int] = []

    def save_sample(content: bytes, frame_seq: int, stats: SystemStats, fps: float) -> bool:
        calls.append(frame_seq)
        started.set()
        release.wait(timeout=2)
        return True

    service._save_sample_frame = save_sample  # type: ignore[method-assign]

    assert service._schedule_sample_frame(b"first-frame", 1, SystemStats(), 15.0) is True
    assert started.wait(timeout=1)
    assert service._schedule_sample_frame(b"second-frame", 2, SystemStats(), 15.0) is False

    release.set()
    assert service._sample_thread is not None
    service._sample_thread.join(timeout=1)
    assert calls == [1]
