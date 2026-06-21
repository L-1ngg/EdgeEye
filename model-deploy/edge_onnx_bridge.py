#!/usr/bin/env python3
"""Run YOLO ONNX inference and build EdgeEye detection upload payloads."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - depends on board image
    raise SystemExit(
        "Missing runtime dependency. Install OpenCV and NumPy, for example: "
        "python3 -m pip install opencv-python numpy"
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT_DIR / "models" / "artifacts" / "detector-transformer-v1.onnx"
DEFAULT_CLASSES = Path(__file__).resolve().parent / "classes-v1.json"
DEFAULT_PREPROCESS = Path(__file__).resolve().parent / "preprocess-v1.json"


@dataclass(frozen=True)
class ClassMapping:
    id: int
    name: str
    category: str
    device_type: str | None
    fault_type: str | None


@dataclass(frozen=True)
class PreprocessConfig:
    input_width: int
    input_height: int
    confidence_threshold: float
    nms_threshold: float
    letterbox: bool


@dataclass(frozen=True)
class InferenceResult:
    detections: list[dict[str, Any]]
    image_width: int
    image_height: int
    latency_ms: float
    fps: float


def main() -> None:
    args = parse_args()
    class_map = load_classes(args.classes)
    preprocess = load_preprocess(args.preprocess)

    result = infer_image(args.model, args.image, class_map, preprocess)
    if args.annotated_output:
        save_annotated_image(args.image, args.annotated_output, result.detections)

    inspection_id = args.inspection_id
    if args.start_inspection:
        if not args.api_base:
            raise SystemExit("--start-inspection requires --api-base")
        inspection_id = start_inspection(args.api_base, args.device_id, args.operator)

    payload = build_payload(
        result=result,
        inspection_id=inspection_id,
        frame_id=args.frame_id,
        frame_seq=args.frame_seq,
        device_id=args.device_id,
        image_url=args.image_url or f"/uploads/raw/local/{args.frame_id}.jpg",
        annotated_image_url=args.annotated_image_url,
        upload_reason=args.upload_reason,
    )

    if args.payload_output:
        args.payload_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    if args.api_base:
        response = post_json(args.api_base, "/detection/results", payload)
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local ONNX detection and optionally upload to EdgeEye backend."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASSES)
    parser.add_argument("--preprocess", type=Path, default=DEFAULT_PREPROCESS)
    parser.add_argument("--api-base", help="Backend API base URL, for example http://localhost:8000/api")
    parser.add_argument("--start-inspection", action="store_true")
    parser.add_argument("--inspection-id", default="inspection-local-0001")
    parser.add_argument("--frame-id", default="frame-000001")
    parser.add_argument("--frame-seq", type=int)
    parser.add_argument("--device-id", default="device-001")
    parser.add_argument("--operator", default="edge")
    parser.add_argument("--upload-reason", default="periodic_sample")
    parser.add_argument("--image-url")
    parser.add_argument("--annotated-image-url")
    parser.add_argument("--annotated-output", type=Path)
    parser.add_argument("--payload-output", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON file: {path}: {exc}") from exc


def load_classes(path: Path) -> dict[int, ClassMapping]:
    data = load_json(path)
    mappings: dict[int, ClassMapping] = {}
    for item in data.get("classes", []):
        class_id = int(item["id"])
        mappings[class_id] = ClassMapping(
            id=class_id,
            name=str(item["name"]),
            category=str(item.get("category") or item["name"]),
            device_type=item.get("deviceType"),
            fault_type=item.get("faultType"),
        )
    if not mappings:
        raise SystemExit(f"No classes configured in {path}")
    return mappings


def load_preprocess(path: Path) -> PreprocessConfig:
    data = load_json(path)
    return PreprocessConfig(
        input_width=int(data["inputWidth"]),
        input_height=int(data["inputHeight"]),
        confidence_threshold=float(data["confidenceThreshold"]),
        nms_threshold=float(data["nmsThreshold"]),
        letterbox=bool(data.get("letterbox", True)),
    )


def infer_image(
    model_path: Path,
    image_path: Path,
    class_map: dict[int, ClassMapping],
    preprocess: PreprocessConfig,
) -> InferenceResult:
    if not model_path.exists():
        raise SystemExit(f"Model file not found: {model_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"Could not read image: {image_path}")

    image_height, image_width = image.shape[:2]
    model_input, scale, pad_x, pad_y = prepare_image(image, preprocess)
    net = cv2.dnn.readNetFromONNX(str(model_path))

    start = time.perf_counter()
    net.setInput(model_input)
    outputs = net.forward(net.getUnconnectedOutLayersNames())
    latency_ms = (time.perf_counter() - start) * 1000.0

    detections = parse_yolo_output(
        outputs[0],
        class_map=class_map,
        preprocess=preprocess,
        image_width=image_width,
        image_height=image_height,
        scale=scale,
        pad_x=pad_x,
        pad_y=pad_y,
    )
    return InferenceResult(
        detections=detections,
        image_width=image_width,
        image_height=image_height,
        latency_ms=round(latency_ms, 3),
        fps=round(1000.0 / latency_ms, 3) if latency_ms > 0 else 0.0,
    )


def prepare_image(image: np.ndarray, config: PreprocessConfig) -> tuple[np.ndarray, float, int, int]:
    if config.letterbox:
        resized, scale, pad_x, pad_y = letterbox(image, config.input_width, config.input_height)
    else:
        original_height, original_width = image.shape[:2]
        resized = cv2.resize(image, (config.input_width, config.input_height), interpolation=cv2.INTER_LINEAR)
        scale = min(config.input_width / original_width, config.input_height / original_height)
        pad_x = 0
        pad_y = 0

    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    tensor = rgb.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[np.newaxis, ...]
    return tensor, scale, pad_x, pad_y


def letterbox(image: np.ndarray, target_width: int, target_height: int) -> tuple[np.ndarray, float, int, int]:
    image_height, image_width = image.shape[:2]
    scale = min(target_width / image_width, target_height / image_height)
    resized_width = int(round(image_width * scale))
    resized_height = int(round(image_height * scale))
    resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((target_height, target_width, 3), 114, dtype=np.uint8)
    pad_x = (target_width - resized_width) // 2
    pad_y = (target_height - resized_height) // 2
    canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized
    return canvas, scale, pad_x, pad_y


def parse_yolo_output(
    output: np.ndarray,
    class_map: dict[int, ClassMapping],
    preprocess: PreprocessConfig,
    image_width: int,
    image_height: int,
    scale: float,
    pad_x: int,
    pad_y: int,
) -> list[dict[str, Any]]:
    predictions = normalize_output_shape(output)
    if predictions.shape[1] < 5:
        raise SystemExit(f"Unexpected YOLO output shape: {output.shape}")

    boxes_xywh: list[list[float]] = []
    backend_boxes: list[tuple[int, int, int, int]] = []
    scores: list[float] = []
    class_ids: list[int] = []

    for prediction in predictions:
        box = prediction[:4]
        class_scores = prediction[4:]
        class_id = int(np.argmax(class_scores))
        confidence = float(class_scores[class_id])
        if confidence < preprocess.confidence_threshold:
            continue

        x1, y1, x2, y2 = to_original_xyxy(
            cx=float(box[0]),
            cy=float(box[1]),
            width=float(box[2]),
            height=float(box[3]),
            image_width=image_width,
            image_height=image_height,
            scale=scale,
            pad_x=pad_x,
            pad_y=pad_y,
        )
        if x2 <= x1 or y2 <= y1:
            continue

        boxes_xywh.append([float(x1), float(y1), float(x2 - x1), float(y2 - y1)])
        backend_boxes.append((x1, y1, x2, y2))
        scores.append(confidence)
        class_ids.append(class_id)

    if not boxes_xywh:
        return []

    indices = cv2.dnn.NMSBoxes(
        boxes_xywh,
        scores,
        preprocess.confidence_threshold,
        preprocess.nms_threshold,
    )
    if len(indices) == 0:
        return []

    detections: list[dict[str, Any]] = []
    for raw_index in np.array(indices).reshape(-1):
        class_id = class_ids[int(raw_index)]
        mapping = class_map.get(class_id)
        if mapping is None:
            mapping = ClassMapping(
                id=class_id,
                name=str(class_id),
                category=str(class_id),
                device_type="unknown",
                fault_type=None,
            )
        detections.append(
            {
                "category": mapping.category,
                "deviceType": mapping.device_type,
                "faultType": mapping.fault_type,
                "confidence": round(scores[int(raw_index)], 4),
                "bbox": list(backend_boxes[int(raw_index)]),
            }
        )
    return sorted(detections, key=lambda item: item["confidence"], reverse=True)


def normalize_output_shape(output: np.ndarray) -> np.ndarray:
    data = np.squeeze(output)
    if data.ndim != 2:
        raise SystemExit(f"Unexpected YOLO output shape: {output.shape}")
    if data.shape[0] < data.shape[1]:
        data = data.T
    return data


def to_original_xyxy(
    cx: float,
    cy: float,
    width: float,
    height: float,
    image_width: int,
    image_height: int,
    scale: float,
    pad_x: int,
    pad_y: int,
) -> tuple[int, int, int, int]:
    x1 = (cx - width / 2.0 - pad_x) / scale
    y1 = (cy - height / 2.0 - pad_y) / scale
    x2 = (cx + width / 2.0 - pad_x) / scale
    y2 = (cy + height / 2.0 - pad_y) / scale
    return (
        clamp_int(x1, 0, image_width - 1),
        clamp_int(y1, 0, image_height - 1),
        clamp_int(x2, 1, image_width),
        clamp_int(y2, 1, image_height),
    )


def clamp_int(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(value))))


def build_payload(
    result: InferenceResult,
    inspection_id: str,
    frame_id: str,
    frame_seq: int | None,
    device_id: str,
    image_url: str,
    annotated_image_url: str | None,
    upload_reason: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "idempotencyKey": f"{inspection_id}:{frame_id}",
        "inspectionId": inspection_id,
        "frameId": frame_id,
        "timestamp": datetime.now().astimezone().isoformat(),
        "deviceId": device_id,
        "isKeyFrame": True,
        "uploadReason": upload_reason,
        "imageUrl": image_url,
        "annotatedImageUrl": annotated_image_url,
        "imageWidth": result.image_width,
        "imageHeight": result.image_height,
        "detections": result.detections,
        "performance": {
            "latencyMs": result.latency_ms,
            "fps": result.fps,
            "cpuUsage": 0,
            "memoryUsage": 0,
            "npuUsage": None,
        },
    }
    if frame_seq is not None:
        payload["frameSeq"] = frame_seq
    return payload


def start_inspection(api_base: str, device_id: str, operator: str) -> str:
    response = post_json(
        api_base,
        "/inspection/start",
        {"deviceId": device_id, "operator": operator, "source": "atlas"},
    )
    try:
        return str(response["data"]["inspectionId"])
    except KeyError as exc:
        raise SystemExit(f"Unexpected start-inspection response: {response}") from exc


def post_json(api_base: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = api_base.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"POST {url} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"POST {url} failed: {exc}") from exc


def save_annotated_image(image_path: Path, output_path: Path, detections: list[dict[str, Any]]) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"Could not read image: {image_path}")
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]
        label = f"{detection['category']} {detection['confidence']:.2f}"
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 220, 120), 2)
        cv2.putText(
            image,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 220, 120),
            2,
            cv2.LINE_AA,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image):
        raise SystemExit(f"Could not write annotated image: {output_path}")


if __name__ == "__main__":
    main()
