from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

BEIJING_TZ = timezone(timedelta(hours=8))
MODULE = "edge-app"
UPLOAD_REASON = "periodic_sample"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


DEFAULTS = {
    "backend_url": "http://localhost:8000/api",
    "uploads_dir": str(repo_root() / "backend" / "uploads"),
    "outbox_dir": str(repo_root() / "edge-app" / "outbox"),
    "source": "/dev/video0",
    "capture_backend": "auto",
    "ffmpeg": "ffmpeg",
    "set_v4l2_format": False,
    "v4l2_ctl": "v4l2-ctl",
    "device_id": "device-001",
    "operator": "edge-camera",
    "inspection_id": None,
    "width": 640,
    "height": 480,
    "interval_seconds": 1.0,
    "timeout_seconds": 5.0,
    "max_frames": 0,
    "start_seq": 1,
    "dry_run": False,
    "once": False,
}

CONFIG_KEY_MAP = {
    "backendUrl": "backend_url",
    "uploadsDir": "uploads_dir",
    "outboxDir": "outbox_dir",
    "source": "source",
    "captureBackend": "capture_backend",
    "ffmpeg": "ffmpeg",
    "setV4l2Format": "set_v4l2_format",
    "v4l2Ctl": "v4l2_ctl",
    "deviceId": "device_id",
    "operator": "operator",
    "inspectionId": "inspection_id",
    "width": "width",
    "height": "height",
    "intervalSeconds": "interval_seconds",
    "timeoutSeconds": "timeout_seconds",
    "maxFrames": "max_frames",
    "startSeq": "start_seq",
    "dryRun": "dry_run",
    "once": "once",
}


@dataclass(frozen=True)
class RuntimeConfig:
    backend_url: str
    uploads_dir: Path
    outbox_dir: Path
    source: str
    capture_backend: str
    ffmpeg: str
    set_v4l2_format: bool
    v4l2_ctl: str
    device_id: str
    operator: str
    inspection_id: Optional[str]
    width: int
    height: int
    interval_seconds: float
    timeout_seconds: float
    max_frames: int
    start_seq: int
    dry_run: bool
    once: bool


@dataclass(frozen=True)
class CapturedFrame:
    path: Path
    image_url: str
    width: int
    height: int
    latency_ms: float


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def start_inspection(self, device_id: str, operator: str) -> str:
        body = {
            "deviceId": device_id,
            "operator": operator,
            "source": "atlas",
        }
        response = self._request("POST", "/inspection/start", body)
        return str(response["data"]["inspectionId"])

    def upload_detection_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/detection/results", payload)

    def _request(self, method: str, path: str, body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method} {path} failed: {exc}") from exc
        if not response_body.get("success", False):
            raise RuntimeError(f"{method} {path} returned API failure: {response_body}")
        return response_body


class CaptureSource:
    def capture(self, output_path: Path, width: int, height: int, timeout_seconds: float) -> None:
        raise NotImplementedError


class V4L2CaptureSource(CaptureSource):
    def __init__(self, device: str, v4l2_ctl: str, set_format: bool) -> None:
        self.device = device
        self.v4l2_ctl = v4l2_ctl
        self.set_format = set_format

    def capture(self, output_path: Path, width: int, height: int, timeout_seconds: float) -> None:
        if shutil.which(self.v4l2_ctl) is None:
            raise RuntimeError(f"{self.v4l2_ctl} not found; install v4l-utils or use --capture-backend opencv")
        command = [
            self.v4l2_ctl,
            f"--device={self.device}",
            "--stream-mmap",
            "--stream-count=1",
            f"--stream-to={output_path}",
        ]
        if self.set_format:
            command.insert(2, f"--set-fmt-video=width={width},height={height},pixelformat=MJPG")
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "unknown v4l2 error").strip()
            raise RuntimeError(f"v4l2 capture failed: {message}")


class OpenCVCaptureSource(CaptureSource):
    def __init__(self, source: str) -> None:
        self.source = source

    def capture(self, output_path: Path, width: int, height: int, timeout_seconds: float) -> None:
        del timeout_seconds
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("OpenCV is not installed") from exc

        cap = cv2.VideoCapture(self.source, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"OpenCV cannot open camera source {self.source}")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise RuntimeError(f"OpenCV read failed for camera source {self.source}")
        if not cv2.imwrite(str(output_path), frame):
            raise RuntimeError(f"OpenCV failed to write {output_path}")


class FFMpegCaptureSource(CaptureSource):
    def __init__(self, source: str, ffmpeg: str) -> None:
        self.source = source
        self.ffmpeg = ffmpeg

    def capture(self, output_path: Path, width: int, height: int, timeout_seconds: float) -> None:
        if shutil.which(self.ffmpeg) is None:
            raise RuntimeError(f"{self.ffmpeg} not found")
        command = [
            self.ffmpeg,
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
            self.source,
            "-frames:v",
            "1",
            str(output_path),
        ]
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "unknown ffmpeg error").strip()
            raise RuntimeError(f"ffmpeg capture failed: {message}")


class AutoCaptureSource(CaptureSource):
    def __init__(self, source: str, ffmpeg: str, v4l2_ctl: str, set_v4l2_format: bool) -> None:
        self.sources = [
            OpenCVCaptureSource(source),
            FFMpegCaptureSource(source, ffmpeg),
            V4L2CaptureSource(source, v4l2_ctl, set_v4l2_format),
        ]
        self.active: Optional[CaptureSource] = None

    def capture(self, output_path: Path, width: int, height: int, timeout_seconds: float) -> None:
        if self.active is not None:
            self.active.capture(output_path, width, height, timeout_seconds)
            return

        errors = []
        for source in self.sources:
            try:
                source.capture(output_path, width, height, timeout_seconds)
                self.active = source
                log_event("capture_backend_selected", backend=source.__class__.__name__)
                return
            except Exception as exc:  # noqa: BLE001 - collect fallback reasons for hardware diagnostics.
                errors.append(f"{source.__class__.__name__}: {exc}")
        raise RuntimeError("; ".join(errors))


class SystemStats:
    def __init__(self) -> None:
        self.previous_cpu: Optional[tuple[int, int]] = None

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


def read_cpu_times() -> Optional[tuple[int, int]]:
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


def now_iso() -> str:
    return datetime.now(BEIJING_TZ).isoformat()


def frame_id(seq: int) -> str:
    return f"frame-{seq:06d}"


def raw_frame_path(uploads_dir: Path, inspection_id: str, frame: str) -> Path:
    return uploads_dir / "raw" / inspection_id / f"{frame}.jpg"


def raw_frame_url(inspection_id: str, frame: str) -> str:
    return f"/uploads/raw/{inspection_id}/{frame}.jpg"


def build_detection_payload(
    *,
    inspection_id: str,
    frame: str,
    frame_seq: int,
    timestamp: str,
    device_id: str,
    image_url: str,
    image_width: int,
    image_height: int,
    latency_ms: float,
    fps: float,
    cpu_usage: float,
    memory_usage: float,
) -> dict[str, Any]:
    return {
        "idempotencyKey": f"{inspection_id}:{frame}",
        "inspectionId": inspection_id,
        "frameId": frame,
        "frameSeq": frame_seq,
        "timestamp": timestamp,
        "deviceId": device_id,
        "isKeyFrame": True,
        "uploadReason": UPLOAD_REASON,
        "imageUrl": image_url,
        "annotatedImageUrl": None,
        "imageWidth": image_width,
        "imageHeight": image_height,
        "detections": [],
        "performance": {
            "latencyMs": round(latency_ms, 2),
            "fps": round(fps, 2),
            "cpuUsage": cpu_usage,
            "memoryUsage": memory_usage,
            "npuUsage": None,
        },
    }


def capture_frame(
    *,
    capture_source: CaptureSource,
    uploads_dir: Path,
    inspection_id: str,
    frame: str,
    width: int,
    height: int,
    timeout_seconds: float,
) -> CapturedFrame:
    output_path = raw_frame_path(uploads_dir, inspection_id, frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    capture_source.capture(output_path, width, height, timeout_seconds)
    latency_ms = (time.monotonic() - started) * 1000
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"camera capture did not create a usable frame: {output_path}")
    return CapturedFrame(
        path=output_path,
        image_url=raw_frame_url(inspection_id, frame),
        width=width,
        height=height,
        latency_ms=latency_ms,
    )


def write_outbox(outbox_dir: Path, payload: dict[str, Any], reason: str) -> Path:
    inspection_id = str(payload["inspectionId"])
    frame = str(payload["frameId"])
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"{inspection_id}-{frame}.json"
    body = {
        "reason": reason,
        "savedAt": now_iso(),
        "payload": payload,
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def log_event(event: str, level: str = "INFO", **fields: Any) -> None:
    body = {
        "timestamp": now_iso(),
        "level": level,
        "module": MODULE,
        "event": event,
    }
    body.update(fields)
    print(json.dumps(body, ensure_ascii=False), flush=True)


def load_config_file(path: Optional[str]) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"config must be a JSON object: {config_path}")
    normalized = {}
    for key, value in data.items():
        normalized_key = CONFIG_KEY_MAP.get(key, key)
        normalized[normalized_key] = value
    return normalized


def parse_args(argv: list[str]) -> RuntimeConfig:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config")
    pre_args, _ = pre_parser.parse_known_args(argv)

    defaults = dict(DEFAULTS)
    defaults.update(load_config_file(pre_args.config))

    parser = argparse.ArgumentParser(
        description="Capture USB camera frames and upload them to the existing EdgeEye backend API.",
    )
    parser.add_argument("--config", default=pre_args.config, help="Path to JSON config file.")
    parser.add_argument("--backend-url", default=defaults["backend_url"])
    parser.add_argument("--uploads-dir", default=defaults["uploads_dir"])
    parser.add_argument("--outbox-dir", default=defaults["outbox_dir"])
    parser.add_argument("--source", default=defaults["source"])
    parser.add_argument(
        "--capture-backend",
        choices=("auto", "ffmpeg", "v4l2", "opencv"),
        default=defaults["capture_backend"],
    )
    parser.add_argument("--ffmpeg", default=defaults["ffmpeg"])
    parser.add_argument(
        "--set-v4l2-format",
        action="store_true",
        default=defaults["set_v4l2_format"],
        help="Set MJPG width/height before streaming. Off by default to avoid busy-device failures.",
    )
    parser.add_argument("--v4l2-ctl", default=defaults["v4l2_ctl"])
    parser.add_argument("--device-id", default=defaults["device_id"])
    parser.add_argument("--operator", default=defaults["operator"])
    parser.add_argument("--inspection-id", default=defaults["inspection_id"])
    parser.add_argument("--width", type=int, default=defaults["width"])
    parser.add_argument("--height", type=int, default=defaults["height"])
    parser.add_argument("--interval-seconds", type=float, default=defaults["interval_seconds"])
    parser.add_argument("--timeout-seconds", type=float, default=defaults["timeout_seconds"])
    parser.add_argument("--max-frames", type=int, default=defaults["max_frames"], help="0 means run until interrupted.")
    parser.add_argument("--start-seq", type=int, default=defaults["start_seq"])
    parser.add_argument("--dry-run", action="store_true", default=defaults["dry_run"])
    parser.add_argument("--once", action="store_true", default=defaults["once"])
    args = parser.parse_args(argv)

    if args.width <= 0 or args.height <= 0:
        raise ValueError("--width and --height must be positive")
    if args.interval_seconds <= 0:
        raise ValueError("--interval-seconds must be positive")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")
    if args.max_frames < 0:
        raise ValueError("--max-frames cannot be negative")
    if args.start_seq <= 0:
        raise ValueError("--start-seq must be positive")

    return RuntimeConfig(
        backend_url=args.backend_url,
        uploads_dir=Path(args.uploads_dir),
        outbox_dir=Path(args.outbox_dir),
        source=args.source,
        capture_backend=args.capture_backend,
        ffmpeg=args.ffmpeg,
        set_v4l2_format=args.set_v4l2_format,
        v4l2_ctl=args.v4l2_ctl,
        device_id=args.device_id,
        operator=args.operator,
        inspection_id=args.inspection_id,
        width=args.width,
        height=args.height,
        interval_seconds=args.interval_seconds,
        timeout_seconds=args.timeout_seconds,
        max_frames=1 if args.once else args.max_frames,
        start_seq=args.start_seq,
        dry_run=args.dry_run,
        once=args.once,
    )


def make_capture_source(config: RuntimeConfig) -> CaptureSource:
    if config.capture_backend == "ffmpeg":
        return FFMpegCaptureSource(config.source, config.ffmpeg)
    if config.capture_backend == "v4l2":
        return V4L2CaptureSource(config.source, config.v4l2_ctl, config.set_v4l2_format)
    if config.capture_backend == "opencv":
        return OpenCVCaptureSource(config.source)
    return AutoCaptureSource(config.source, config.ffmpeg, config.v4l2_ctl, config.set_v4l2_format)


def run(config: RuntimeConfig) -> int:
    client = BackendClient(config.backend_url, config.timeout_seconds)
    capture_source = make_capture_source(config)
    stats = SystemStats()

    inspection_id = config.inspection_id
    if inspection_id is None:
        if config.dry_run:
            inspection_id = "inspection-dry-run"
        else:
            client.get_health()
            inspection_id = client.start_inspection(config.device_id, config.operator)
            log_event("inspection_started", inspectionId=inspection_id, deviceId=config.device_id)
    else:
        log_event("inspection_reused", inspectionId=inspection_id, deviceId=config.device_id)

    sent = 0
    seq = config.start_seq
    while config.max_frames == 0 or sent < config.max_frames:
        loop_started = time.monotonic()
        frame = frame_id(seq)
        timestamp = now_iso()
        payload = None
        try:
            captured = capture_frame(
                capture_source=capture_source,
                uploads_dir=config.uploads_dir,
                inspection_id=inspection_id,
                frame=frame,
                width=config.width,
                height=config.height,
                timeout_seconds=config.timeout_seconds,
            )
            elapsed = max(time.monotonic() - loop_started, 0.001)
            cpu_usage, memory_usage = stats.snapshot()
            payload = build_detection_payload(
                inspection_id=inspection_id,
                frame=frame,
                frame_seq=seq,
                timestamp=timestamp,
                device_id=config.device_id,
                image_url=captured.image_url,
                image_width=captured.width,
                image_height=captured.height,
                latency_ms=captured.latency_ms,
                fps=1.0 / elapsed,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
            )
            if config.dry_run:
                log_event("dry_run_payload", inspectionId=inspection_id, frameId=frame, payload=payload)
            else:
                response = client.upload_detection_result(payload)
                data = response["data"]
                log_event(
                    "detection_uploaded",
                    inspectionId=inspection_id,
                    frameId=frame,
                    resultId=data["resultId"],
                    duplicate=data["duplicate"],
                    imageUrl=captured.image_url,
                    latencyMs=round(captured.latency_ms, 2),
                )
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - edge loop must log and continue on hardware/network failures.
            log_event("frame_upload_failed", level="ERROR", inspectionId=inspection_id, frameId=frame, error=str(exc))
            if payload is not None:
                outbox_path = write_outbox(config.outbox_dir, payload, str(exc))
                log_event("outbox_saved", inspectionId=inspection_id, frameId=frame, path=str(outbox_path))
            if config.once:
                return 1

        sent += 1
        seq += 1
        remaining = config.interval_seconds - (time.monotonic() - loop_started)
        if remaining > 0 and (config.max_frames == 0 or sent < config.max_frames):
            time.sleep(remaining)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        config = parse_args(sys.argv[1:] if argv is None else argv)
        return run(config)
    except KeyboardInterrupt:
        log_event("stopped_by_user")
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI entrypoint should print concise diagnostics.
        log_event("startup_failed", level="ERROR", error=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
