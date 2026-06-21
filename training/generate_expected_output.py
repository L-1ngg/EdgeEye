from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from ultralytics import YOLO


TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def dataset_base(dataset_path: Path, data: dict[str, Any]) -> Path:
    raw_path = data.get("path")
    if raw_path is None:
        return dataset_path.parent
    path = Path(str(raw_path))
    return path if path.is_absolute() else (dataset_path.parent / path).resolve()


def image_paths(dataset_path: Path, split: str, max_candidates: int) -> list[Path]:
    data = load_dataset(dataset_path)
    if split not in data:
        raise ValueError(f"{dataset_path} does not define split {split!r}")
    image_dir = dataset_base(dataset_path, data) / str(data[split])
    if not image_dir.is_dir():
        raise ValueError(f"Image directory not found: {image_dir}")
    paths = [
        path
        for path in sorted(image_dir.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    return paths[:max_candidates]


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def round_bbox(values: list[float]) -> list[int]:
    return [int(round(value)) for value in values]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate EdgeEye detector expected outputs from development-machine inference."
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "best.pt",
        help="Model weights used as the development-machine reference",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "dataset" / "processed" / "edgeeye-detector-v1" / "dataset.yaml",
        help="YOLO dataset.yaml path",
    )
    parser.add_argument(
        "--classes",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "classes.json",
        help="classes.json with contract mappings",
    )
    parser.add_argument(
        "--preprocess",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "preprocess-v1.json",
        help="preprocess-v1.json with inference thresholds",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "expected-output-v1.json",
        help="Expected output JSON path",
    )
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--min-cases", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--max-detections-per-image", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=None)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    args.weights = args.weights.expanduser().resolve()
    args.dataset = args.dataset.expanduser().resolve()
    args.classes = args.classes.expanduser().resolve()
    args.preprocess = args.preprocess.expanduser().resolve()
    args.output = args.output.expanduser().resolve()

    if not args.weights.is_file():
        raise SystemExit(f"Missing weights: {args.weights}")
    if not args.classes.is_file():
        raise SystemExit(f"Missing classes file: {args.classes}")
    if not args.preprocess.is_file():
        raise SystemExit(f"Missing preprocess file: {args.preprocess}")

    class_config = load_json(args.classes)
    preprocess = load_json(args.preprocess)
    classes = {int(item["id"]): item for item in class_config["classes"]}
    conf = args.conf if args.conf is not None else float(preprocess["confidenceThreshold"])
    iou = args.iou if args.iou is not None else float(preprocess["nmsThreshold"])

    model = YOLO(str(args.weights))
    cases: list[dict[str, Any]] = []

    for image_path in image_paths(args.dataset, args.split, args.max_candidates):
        predict_kwargs: dict[str, Any] = {
            "source": str(image_path),
            "imgsz": args.imgsz,
            "conf": conf,
            "iou": iou,
            "verbose": False,
        }
        if args.device is not None:
            predict_kwargs["device"] = args.device

        result = model.predict(**predict_kwargs)[0]
        detections: list[dict[str, Any]] = []
        if result.boxes is not None:
            for box in result.boxes[: args.max_detections_per_image]:
                class_id = int(box.cls[0].item())
                class_info = classes[class_id]
                confidence = float(box.conf[0].item())
                detections.append(
                    {
                        "classId": class_id,
                        "className": class_info["name"],
                        "confidence": round(confidence, 6),
                        "bbox": round_bbox(box.xyxy[0].tolist()),
                        "deviceType": class_info.get("deviceType"),
                        "faultType": class_info.get("faultType"),
                    }
                )

        if not detections:
            continue

        height, width = result.orig_shape
        cases.append(
            {
                "image": repo_relative(image_path),
                "width": int(width),
                "height": int(height),
                "detections": detections,
            }
        )
        if len(cases) >= args.min_cases:
            break

    if len(cases) < args.min_cases:
        raise SystemExit(
            f"Only found {len(cases)} images with detections above conf={conf}; "
            f"increase --max-candidates or lower --conf."
        )

    output = {
        "version": class_config.get("version", "edgeeye-detector-v1"),
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {
            "weights": repo_relative(args.weights),
            "dataset": repo_relative(args.dataset),
            "split": args.split,
            "imgsz": args.imgsz,
            "confidenceThreshold": conf,
            "nmsThreshold": iou,
            "maxDetectionsPerImage": args.max_detections_per_image,
        },
        "comparisonTolerance": {
            "bboxPixels": 4,
            "confidenceAbsolute": 0.05,
        },
        "classes": class_config["classes"],
        "cases": cases,
        "notes": [
            "Generated from development-machine Ultralytics inference.",
            "Use tolerances for Atlas .om comparison because runtime kernels can shift confidence slightly.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} expected-output cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
