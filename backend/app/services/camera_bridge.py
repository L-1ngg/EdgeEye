from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.inspection import DetectionUploadRequest, Performance, StartInspectionRequest
from app.services.inspection_service import current_timestamp, get_service

logger = logging.getLogger(__name__)

UPLOAD_REASON = "periodic_sample"


@dataclass(frozen=True)
class CapturedFrame:
    path: Path
    image_url: str
    latency_ms: float
    backend: str


class CameraCaptureError(RuntimeError):
    pass


class CameraBridgeService:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._inspection_id: str | None = None
        self._active_backend: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if not settings.camera_bridge_enabled:
                logger.info("camera bridge disabled by configuration")
                return
            if not self._source_is_available():
                logger.warning("camera bridge skipped; source is unavailable: %s", settings.camera_source)
                return

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="edgeeye-camera-bridge", daemon=True)
            self._thread.start()
            logger.info("camera bridge started")

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is None:
            return
        self._stop_event.set()
        thread.join(timeout=3)
        logger.info("camera bridge stopped")

    def _source_is_available(self) -> bool:
        source = settings.camera_source
        if source.startswith("/dev/"):
            return Path(source).exists()
        return True

    def _run(self) -> None:
        frame_seq = 1
        stats = SystemStats()
        while not self._stop_event.is_set():
            loop_started = time.monotonic()
            payload = None
            try:
                inspection_id = self._ensure_inspection()
                frame_id = format_frame_id(frame_seq)
                timestamp = current_timestamp()
                captured = capture_frame(
                    source=settings.camera_source,
                    backend=settings.camera_capture_backend,
                    ffmpeg=settings.camera_ffmpeg_path,
                    v4l2_ctl=settings.camera_v4l2_ctl_path,
                    uploads_dir=Path(settings.uploads_dir),
                    inspection_id=inspection_id,
                    frame_id=frame_id,
                    width=settings.camera_width,
                    height=settings.camera_height,
                    timeout_seconds=settings.camera_timeout_seconds,
                    preferred_backend=self._active_backend,
                )
                self._active_backend = captured.backend
                elapsed = max(time.monotonic() - loop_started, 0.001)
                cpu_usage, memory_usage = stats.snapshot()
                payload = build_camera_payload(
                    inspection_id=inspection_id,
                    frame_id=frame_id,
                    frame_seq=frame_seq,
                    timestamp=timestamp,
                    device_id=settings.camera_device_id,
                    image_url=captured.image_url,
                    image_width=settings.camera_width,
                    image_height=settings.camera_height,
                    latency_ms=captured.latency_ms,
                    fps=1.0 / elapsed,
                    cpu_usage=cpu_usage,
                    memory_usage=memory_usage,
                )
                result = get_service().upload_detection_result(payload)
                logger.info(
                    "camera frame uploaded inspection_id=%s frame_id=%s result_id=%s image_url=%s",
                    inspection_id,
                    frame_id,
                    result.resultId,
                    captured.image_url,
                )
                frame_seq += 1
            except Exception as exc:  # noqa: BLE001 - background bridge must not crash the API process.
                logger.warning("camera bridge frame failed: %s", exc)
                if payload is not None:
                    save_outbox(Path(settings.camera_outbox_dir), payload, str(exc))

            remaining = settings.camera_interval_seconds - (time.monotonic() - loop_started)
            self._stop_event.wait(max(remaining, 0.1))

    def _ensure_inspection(self) -> str:
        if self._inspection_id is not None:
            return self._inspection_id
        result = get_service().start_inspection(
            StartInspectionRequest(
                deviceId=settings.camera_device_id,
                operator=settings.camera_operator,
                source="atlas",
            )
        )
        self._inspection_id = result.inspectionId
        logger.info("camera inspection started inspection_id=%s", self._inspection_id)
        return self._inspection_id


def format_frame_id(seq: int) -> str:
    return f"frame-{seq:06d}"


def raw_frame_path(uploads_dir: Path, inspection_id: str, frame_id: str) -> Path:
    return uploads_dir / "raw" / inspection_id / f"{frame_id}.jpg"


def raw_frame_url(inspection_id: str, frame_id: str) -> str:
    return f"/uploads/raw/{inspection_id}/{frame_id}.jpg"


def build_camera_payload(
    *,
    inspection_id: str,
    frame_id: str,
    frame_seq: int,
    timestamp: Any,
    device_id: str,
    image_url: str,
    image_width: int,
    image_height: int,
    latency_ms: float,
    fps: float,
    cpu_usage: float,
    memory_usage: float,
) -> DetectionUploadRequest:
    return DetectionUploadRequest(
        idempotencyKey=f"{inspection_id}:{frame_id}",
        inspectionId=inspection_id,
        frameId=frame_id,
        frameSeq=frame_seq,
        timestamp=timestamp,
        deviceId=device_id,
        isKeyFrame=True,
        uploadReason=UPLOAD_REASON,
        imageUrl=image_url,
        annotatedImageUrl=None,
        imageWidth=image_width,
        imageHeight=image_height,
        detections=[],
        performance=Performance(
            latencyMs=round(latency_ms, 2),
            fps=round(fps, 2),
            cpuUsage=cpu_usage,
            memoryUsage=memory_usage,
            npuUsage=None,
        ),
    )


def capture_frame(
    *,
    source: str,
    backend: str,
    ffmpeg: str,
    v4l2_ctl: str,
    uploads_dir: Path,
    inspection_id: str,
    frame_id: str,
    width: int,
    height: int,
    timeout_seconds: float,
    preferred_backend: str | None = None,
) -> CapturedFrame:
    output_path = raw_frame_path(uploads_dir, inspection_id, frame_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    errors = []
    candidates = capture_candidates(backend, preferred_backend)
    for candidate in candidates:
        try:
            if candidate == "ffmpeg":
                capture_with_ffmpeg(ffmpeg, source, output_path, width, height, timeout_seconds)
            elif candidate == "v4l2":
                capture_with_v4l2(v4l2_ctl, source, output_path, timeout_seconds)
            else:
                raise CameraCaptureError(f"unsupported capture backend: {candidate}")
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise CameraCaptureError(f"capture produced an empty frame: {output_path}")
            return CapturedFrame(
                path=output_path,
                image_url=raw_frame_url(inspection_id, frame_id),
                latency_ms=(time.monotonic() - started) * 1000,
                backend=candidate,
            )
        except Exception as exc:  # noqa: BLE001 - collect all backend failures for diagnostics.
            errors.append(f"{candidate}: {exc}")
    raise CameraCaptureError("; ".join(errors))


def capture_candidates(backend: str, preferred_backend: str | None = None) -> list[str]:
    fallback = ["ffmpeg", "v4l2"] if backend == "auto" else [backend]
    if preferred_backend:
        return [preferred_backend, *[item for item in fallback if item != preferred_backend]]
    return fallback


def capture_with_ffmpeg(
    ffmpeg: str,
    source: str,
    output_path: Path,
    width: int,
    height: int,
    timeout_seconds: float,
) -> None:
    if shutil.which(ffmpeg) is None:
        raise CameraCaptureError(f"{ffmpeg} not found")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "v4l2",
        "-input_format",
        "mjpeg",
        "-video_size",
        f"{width}x{height}",
        "-i",
        source,
        "-frames:v",
        "1",
        str(output_path),
    ]
    run_capture_command(command, timeout_seconds, "ffmpeg")


def capture_with_v4l2(v4l2_ctl: str, source: str, output_path: Path, timeout_seconds: float) -> None:
    if shutil.which(v4l2_ctl) is None:
        raise CameraCaptureError(f"{v4l2_ctl} not found")
    command = [
        v4l2_ctl,
        f"--device={source}",
        "--stream-mmap",
        "--stream-count=1",
        f"--stream-to={output_path}",
    ]
    run_capture_command(command, timeout_seconds, "v4l2")


def run_capture_command(command: list[str], timeout_seconds: float, label: str) -> None:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or f"{label} exited with {result.returncode}").strip()
        raise CameraCaptureError(message)


def save_outbox(outbox_dir: Path, payload: DetectionUploadRequest, reason: str) -> Path:
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"{payload.inspectionId}-{payload.frameId}.json"
    body = {
        "reason": reason,
        "savedAt": current_timestamp().isoformat(),
        "payload": payload.model_dump(mode="json"),
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class SystemStats:
    def __init__(self) -> None:
        self.previous_cpu: tuple[int, int] | None = None

    def snapshot(self) -> tuple[float, float]:
        return self.cpu_usage_percent(), memory_usage_percent()

    def cpu_usage_percent(self) -> float:
        current = read_cpu_times()
        if current is None:
            return 0.0
        if self.previous_cpu is None:
            self.previous_cpu = current
            return 0.0
        previous_idle, previous_total = self.previous_cpu
        idle, total = current
        self.previous_cpu = current
        total_delta = total - previous_total
        idle_delta = idle - previous_idle
        if total_delta <= 0:
            return 0.0
        return round(max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0)), 1)


def read_cpu_times() -> tuple[int, int] | None:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            parts = handle.readline().split()
    except OSError:
        return None
    if not parts or parts[0] != "cpu":
        return None
    values = [int(value) for value in parts[1:]]
    if len(values) < 4:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return idle, sum(values)


def memory_usage_percent() -> float:
    values: dict[str, int] = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                key, raw_value = line.split(":", 1)
                values[key] = int(raw_value.strip().split()[0])
    except (OSError, ValueError):
        return 0.0
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    if total <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (1.0 - available / total) * 100.0)), 1)


camera_bridge_service = CameraBridgeService()
