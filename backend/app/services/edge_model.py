from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.models.inspection import Detection

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class EdgeModelResult:
    detections: list[Detection]
    image_width: int
    image_height: int
    latency_ms: float
    fps: float
    annotated_image_path: Path | None


class EdgeModelBridgeError(RuntimeError):
    pass


class EdgeModelInferenceService:
    def __init__(self) -> None:
        self._warned_reasons: set[str] = set()

    def infer_frame(self, image_path: Path, annotated_path: Path | None) -> EdgeModelResult | None:
        if not settings.edge_model_enabled:
            return None
        try:
            return self._infer_frame(image_path=image_path, annotated_path=annotated_path)
        except Exception as exc:  # noqa: BLE001 - camera sampling must degrade to no-model upload.
            self._warn_once(str(exc))
            return None

    def _infer_frame(self, image_path: Path, annotated_path: Path | None) -> EdgeModelResult:
        image_path = image_path.resolve()
        annotated_path = annotated_path.resolve() if annotated_path is not None else None
        model_path = resolve_project_path(settings.edge_model_path)
        script_path = resolve_project_path(settings.edge_model_script)
        classes_path = resolve_project_path(settings.edge_model_classes_path)
        preprocess_path = resolve_project_path(settings.edge_model_preprocess_path)
        ensure_file(model_path, "edge model")
        ensure_file(script_path, "edge model script")
        ensure_file(classes_path, "edge model classes")
        ensure_file(preprocess_path, "edge model preprocess")
        ensure_file(image_path, "camera sample")

        command = [
            resolve_python_executable(settings.edge_model_python),
            str(script_path),
            "--model",
            str(model_path),
            "--image",
            str(image_path),
            "--classes",
            str(classes_path),
            "--preprocess",
            str(preprocess_path),
            "--device-id",
            str(settings.edge_model_device_id),
            "--output-shape",
            settings.edge_model_output_shape,
        ]
        if annotated_path is not None:
            command.extend(["--annotated-output", str(annotated_path)])

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            cwd=PROJECT_ROOT,
            text=True,
            timeout=settings.edge_model_timeout_seconds,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or f"exit={result.returncode}").strip()
            raise EdgeModelBridgeError(f"edge model bridge failed: {truncate_detail(detail)}")
        return parse_bridge_output(result.stdout, annotated_path)

    def _warn_once(self, reason: str) -> None:
        key = truncate_detail(reason)
        if key in self._warned_reasons:
            return
        self._warned_reasons.add(key)
        logger.warning("edge model inference skipped: %s", key)


def resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        PROJECT_ROOT / path,
        PROJECT_ROOT / "backend" / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / path


def resolve_python_executable(value: str) -> str:
    path = Path(value).expanduser()
    if path.is_absolute() or "/" in value:
        return str(path)
    if value == "python3":
        for candidate in [Path("/usr/local/miniconda3/bin/python3"), Path("/usr/bin/python3")]:
            if candidate.is_file():
                return str(candidate)
    return value


def ensure_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise EdgeModelBridgeError(f"{label} not found: {path}")


def parse_bridge_output(stdout: str, annotated_path: Path | None) -> EdgeModelResult:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise EdgeModelBridgeError("edge model bridge produced no JSON output")
    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise EdgeModelBridgeError(f"edge model bridge produced invalid JSON: {exc}") from exc

    try:
        detections = [Detection(**item) for item in data.get("detections", [])]
    except (TypeError, ValidationError) as exc:
        raise EdgeModelBridgeError(f"edge model bridge produced invalid detections: {exc}") from exc

    try:
        image_width = int(data["imageWidth"])
        image_height = int(data["imageHeight"])
        latency_ms = float(data["latencyMs"])
        fps = float(data.get("fps") or 0.0)
    except (KeyError, TypeError, ValueError) as exc:
        raise EdgeModelBridgeError(f"edge model bridge output is missing required fields: {exc}") from exc

    if annotated_path is not None and not annotated_path.is_file():
        raise EdgeModelBridgeError(f"annotated image was not created: {annotated_path}")

    return EdgeModelResult(
        detections=detections,
        image_width=image_width,
        image_height=image_height,
        latency_ms=max(0.0, latency_ms),
        fps=max(0.0, fps),
        annotated_image_path=annotated_path,
    )


def truncate_detail(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3] + "..."


edge_model_service = EdgeModelInferenceService()
