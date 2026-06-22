from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.inspection import Detection, DetectionUploadRequest, Performance, StartInspectionRequest
from app.services.edge_model import edge_model_service
from app.services.inspection_service import current_timestamp, get_service

logger = logging.getLogger(__name__)

UPLOAD_REASON = "periodic_sample"
MJPEG_BOUNDARY = "frame"
JPEG_START = b"\xff\xd8"
JPEG_END = b"\xff\xd9"


@dataclass(frozen=True)
class CapturedFrame:
    path: Path
    image_url: str
    latency_ms: float
    backend: str


@dataclass(frozen=True)
class StreamFrame:
    sequence: int
    content: bytes
    captured_at: float


class CameraCaptureError(RuntimeError):
    pass


class CameraBridgeService:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._condition = threading.Condition()
        self._inspection_id: str | None = None
        self._active_backend: str | None = None
        self._latest_frame: StreamFrame | None = None
        self._stream_error: str | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._sample_lock = threading.Lock()
        self._sample_thread: threading.Thread | None = None

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
            with self._condition:
                self._latest_frame = None
                self._stream_error = None
                self._condition.notify_all()
            self._thread = threading.Thread(target=self._run, name="edgeeye-camera-bridge", daemon=True)
            self._thread.start()
            logger.info("camera bridge started")

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._thread = None
            self._stop_event.set()
            self._terminate_stream_process()
        with self._sample_lock:
            sample_thread = self._sample_thread
        with self._condition:
            self._condition.notify_all()
        if thread is None:
            return
        thread.join(timeout=3)
        if sample_thread is not None:
            sample_thread.join(timeout=3)
        logger.info("camera bridge stopped")

    def ensure_stream_available(self) -> None:
        if not settings.camera_bridge_enabled:
            raise CameraCaptureError("camera bridge is disabled")
        if shutil.which(settings.camera_ffmpeg_path) is None:
            raise CameraCaptureError(f"{settings.camera_ffmpeg_path} not found")
        if not self._source_is_available():
            raise CameraCaptureError(f"camera source is unavailable: {settings.camera_source}")
        self.start()
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                raise CameraCaptureError("camera bridge is not running")
        self._wait_until_stream_ready(settings.camera_timeout_seconds)

    def iter_mjpeg_stream(self) -> Iterator[bytes]:
        self.ensure_stream_available()
        last_sequence = 0
        while not self._stop_event.is_set():
            frame = self._wait_for_stream_frame(last_sequence, settings.camera_timeout_seconds)
            if frame is None:
                continue
            last_sequence = frame.sequence
            yield mjpeg_part(frame.content)

    def _source_is_available(self) -> bool:
        source = settings.camera_source
        if source.startswith("/dev/"):
            return Path(source).exists()
        return True

    def _run(self) -> None:
        stream_seq = 0
        sample_seq = 1
        last_sample_at = 0.0
        stats = SystemStats()
        fps_meter = FpsMeter()
        while not self._stop_event.is_set():
            process: subprocess.Popen[bytes] | None = None
            try:
                process = open_ffmpeg_mjpeg_stream(
                    ffmpeg=settings.camera_ffmpeg_path,
                    source=settings.camera_source,
                    width=settings.camera_width,
                    height=settings.camera_height,
                    fps=settings.camera_stream_fps,
                )
                with self._lock:
                    self._process = process
                    self._active_backend = "ffmpeg-stream"
                for content in iter_jpeg_frames_from_process(process, self._stop_event):
                    if self._stop_event.is_set():
                        break
                    now = time.monotonic()
                    stream_seq += 1
                    measured_fps = fps_meter.tick(now)
                    self._publish_stream_frame(StreamFrame(sequence=stream_seq, content=content, captured_at=now))
                    if now - last_sample_at >= settings.camera_interval_seconds:
                        if self._schedule_sample_frame(content, sample_seq, stats, measured_fps):
                            last_sample_at = now
                            sample_seq += 1
                if not self._stop_event.is_set():
                    raise CameraCaptureError(read_process_error(process) or "ffmpeg camera stream exited")
            except Exception as exc:  # noqa: BLE001 - background bridge must not crash the API process.
                self._set_stream_error(str(exc))
                logger.warning("camera bridge stream failed: %s", exc)
                self._stop_event.wait(1.0)
            finally:
                if process is not None:
                    terminate_process(process)
                with self._lock:
                    if self._process is process:
                        self._process = None

    def _wait_for_stream_frame(self, last_sequence: int, timeout_seconds: float) -> StreamFrame | None:
        deadline = time.monotonic() + timeout_seconds
        with self._condition:
            while not self._stop_event.is_set():
                if self._latest_frame is not None and self._latest_frame.sequence != last_sequence:
                    return self._latest_frame
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(timeout=remaining)
        return None

    def _wait_until_stream_ready(self, timeout_seconds: float) -> None:
        deadline = time.monotonic() + timeout_seconds
        with self._condition:
            while self._latest_frame is None and not self._stop_event.is_set():
                if self._stream_error:
                    raise CameraCaptureError(self._stream_error)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CameraCaptureError("camera stream did not produce a frame before timeout")
                self._condition.wait(timeout=remaining)

    def _publish_stream_frame(self, frame: StreamFrame) -> None:
        with self._condition:
            self._latest_frame = frame
            self._stream_error = None
            self._condition.notify_all()

    def _set_stream_error(self, message: str) -> None:
        with self._condition:
            self._stream_error = message
            self._condition.notify_all()

    def _save_sample_frame(self, content: bytes, frame_seq: int, stats: SystemStats, fps: float) -> bool:
        payload = None
        try:
            inspection_id = self._ensure_inspection()
            frame_id = format_frame_id(frame_seq)
            timestamp = current_timestamp()
            captured = save_frame_bytes(
                content=content,
                uploads_dir=Path(settings.uploads_dir),
                inspection_id=inspection_id,
                frame_id=frame_id,
                backend=self._active_backend or "ffmpeg-stream",
            )
            annotated_path = (
                annotated_frame_path(Path(settings.uploads_dir), inspection_id, frame_id)
                if settings.edge_model_annotated_enabled
                else None
            )
            model_result = edge_model_service.infer_frame(captured.path, annotated_path)
            detections: Sequence[Detection] = model_result.detections if model_result is not None else []
            annotated_image_url = (
                annotated_frame_url(inspection_id, frame_id)
                if model_result is not None and model_result.annotated_image_path is not None
                else None
            )
            image_width = model_result.image_width if model_result is not None else settings.camera_width
            image_height = model_result.image_height if model_result is not None else settings.camera_height
            model_latency_ms = model_result.latency_ms if model_result is not None else 0.0
            cpu_usage, memory_usage = stats.snapshot()
            payload = build_camera_payload(
                inspection_id=inspection_id,
                frame_id=frame_id,
                frame_seq=frame_seq,
                timestamp=timestamp,
                device_id=settings.camera_device_id,
                image_url=captured.image_url,
                annotated_image_url=annotated_image_url,
                image_width=image_width,
                image_height=image_height,
                detections=detections,
                latency_ms=captured.latency_ms + model_latency_ms,
                fps=fps,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
            )
            result = get_service().upload_detection_result(payload)
            prune_raw_frames(
                uploads_dir=Path(settings.uploads_dir),
                inspection_id=inspection_id,
                keep_count=settings.camera_max_raw_frames_per_inspection,
            )
            prune_annotated_frames(
                uploads_dir=Path(settings.uploads_dir),
                inspection_id=inspection_id,
                keep_count=settings.camera_max_raw_frames_per_inspection,
            )
            logger.info(
                "camera sample uploaded inspection_id=%s frame_id=%s result_id=%s detections=%s image_url=%s",
                inspection_id,
                frame_id,
                result.resultId,
                len(detections),
                captured.image_url,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - sampling failures should not stop realtime streaming.
            logger.warning("camera sample failed: %s", exc)
            if payload is not None:
                save_outbox(Path(settings.camera_outbox_dir), payload, str(exc))
                return True
            return False

    def _schedule_sample_frame(self, content: bytes, frame_seq: int, stats: SystemStats, fps: float) -> bool:
        with self._sample_lock:
            if self._sample_thread is not None and self._sample_thread.is_alive():
                return False
            self._sample_thread = threading.Thread(
                target=self._save_sample_frame,
                args=(content, frame_seq, stats, fps),
                name="edgeeye-camera-sample",
                daemon=True,
            )
            self._sample_thread.start()
            return True

    def _terminate_stream_process(self) -> None:
        process = self._process
        self._process = None
        if process is not None:
            terminate_process(process)

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


def annotated_frame_path(uploads_dir: Path, inspection_id: str, frame_id: str) -> Path:
    return uploads_dir / "annotated" / inspection_id / f"{frame_id}.jpg"


def annotated_frame_url(inspection_id: str, frame_id: str) -> str:
    return f"/uploads/annotated/{inspection_id}/{frame_id}.jpg"


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
    annotated_image_url: str | None = None,
    detections: Sequence[Detection] | None = None,
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
        annotatedImageUrl=annotated_image_url,
        imageWidth=image_width,
        imageHeight=image_height,
        detections=list(detections or []),
        performance=Performance(
            latencyMs=round(latency_ms, 2),
            fps=round(fps, 2),
            cpuUsage=cpu_usage,
            memoryUsage=memory_usage,
            npuUsage=None,
        ),
    )


def save_frame_bytes(
    *,
    content: bytes,
    uploads_dir: Path,
    inspection_id: str,
    frame_id: str,
    backend: str,
) -> CapturedFrame:
    if not content:
        raise CameraCaptureError("empty camera frame")
    started = time.monotonic()
    output_path = raw_frame_path(uploads_dir, inspection_id, frame_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return CapturedFrame(
        path=output_path,
        image_url=raw_frame_url(inspection_id, frame_id),
        latency_ms=(time.monotonic() - started) * 1000,
        backend=backend,
    )


def mjpeg_part(content: bytes) -> bytes:
    return (
        f"--{MJPEG_BOUNDARY}\r\n"
        "Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(content)}\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    ).encode("ascii") + content + b"\r\n"


def open_ffmpeg_mjpeg_stream(
    *,
    ffmpeg: str,
    source: str,
    width: int,
    height: int,
    fps: int,
) -> subprocess.Popen[bytes]:
    if shutil.which(ffmpeg) is None:
        raise CameraCaptureError(f"{ffmpeg} not found")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "nobuffer",
        "-f",
        "v4l2",
        "-input_format",
        "mjpeg",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        source,
        "-an",
        "-c:v",
        "copy",
        "-flush_packets",
        "1",
        "-f",
        "mjpeg",
        "-",
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def iter_jpeg_frames_from_process(
    process: subprocess.Popen[bytes],
    stop_event: threading.Event,
) -> Iterator[bytes]:
    if process.stdout is None:
        raise CameraCaptureError("ffmpeg stream stdout is unavailable")
    buffer = bytearray()
    while not stop_event.is_set():
        chunk = process.stdout.read(4096)
        if not chunk:
            break
        yield from extract_jpeg_frames(buffer, chunk)


def extract_jpeg_frames(buffer: bytearray, chunk: bytes) -> Iterator[bytes]:
    buffer.extend(chunk)
    while True:
        start = buffer.find(JPEG_START)
        if start < 0:
            del buffer[:-1]
            return
        end = buffer.find(JPEG_END, start + len(JPEG_START))
        if end < 0:
            if start > 0:
                del buffer[:start]
            if len(buffer) > 10_000_000:
                del buffer[:-1]
            return
        frame_end = end + len(JPEG_END)
        frame = bytes(buffer[start:frame_end])
        del buffer[:frame_end]
        yield frame


def read_process_error(process: subprocess.Popen[bytes]) -> str:
    if process.stderr is None:
        return ""
    if process.poll() is None:
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            return ""
    try:
        message = process.stderr.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""
    return message or f"ffmpeg exited with {process.returncode}"


def terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def prune_raw_frames(*, uploads_dir: Path, inspection_id: str, keep_count: int) -> list[Path]:
    return prune_upload_frames(
        uploads_dir=uploads_dir,
        inspection_id=inspection_id,
        keep_count=keep_count,
        kind="raw",
    )


def prune_annotated_frames(*, uploads_dir: Path, inspection_id: str, keep_count: int) -> list[Path]:
    return prune_upload_frames(
        uploads_dir=uploads_dir,
        inspection_id=inspection_id,
        keep_count=keep_count,
        kind="annotated",
    )


def prune_upload_frames(*, uploads_dir: Path, inspection_id: str, keep_count: int, kind: str) -> list[Path]:
    if keep_count <= 0:
        return []
    frame_dir = uploads_dir / kind / inspection_id
    if not frame_dir.exists():
        return []
    frames = sorted(
        (path for path in frame_dir.glob("frame-*.jpg") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    excess_count = len(frames) - keep_count
    if excess_count <= 0:
        return []
    deleted: list[Path] = []
    for path in frames[:excess_count]:
        try:
            path.unlink()
            deleted.append(path)
        except FileNotFoundError:
            continue
    return deleted


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


class FpsMeter:
    def __init__(self) -> None:
        self.previous_frame_at: float | None = None
        self.current_fps = 0.0

    def tick(self, captured_at: float) -> float:
        if self.previous_frame_at is None:
            self.previous_frame_at = captured_at
            self.current_fps = float(settings.camera_stream_fps)
            return self.current_fps
        elapsed = captured_at - self.previous_frame_at
        self.previous_frame_at = captured_at
        if elapsed <= 0:
            return self.current_fps
        self.current_fps = 1.0 / elapsed
        return self.current_fps


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
