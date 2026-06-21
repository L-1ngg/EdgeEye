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


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset_names(dataset: Path) -> list[str]:
    data = yaml.safe_load(dataset.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{dataset} must contain a YAML mapping")
    names = data.get("names")
    if isinstance(names, list):
        return [str(name) for name in names]
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names)]
    raise ValueError(f"{dataset} must define names")


def load_dataset(dataset: Path) -> dict[str, Any]:
    data = yaml.safe_load(dataset.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{dataset} must contain a YAML mapping")
    return data


def dataset_base(dataset: Path, data: dict[str, Any]) -> Path:
    raw_path = data.get("path")
    if raw_path is None:
        return dataset.parent
    path = Path(str(raw_path))
    return path if path.is_absolute() else (dataset.parent / path).resolve()


def infer_source(image_name: str) -> str:
    if image_name.startswith("dataset-ninja_"):
        return "dataset-ninja"
    if image_name.startswith("datasetninja_"):
        return "dataset-ninja"
    if image_name.startswith("aerial_"):
        return "aerial"
    if image_name.startswith("substation_"):
        return "substation"
    if image_name.startswith("transformer_"):
        return "transformer"
    return "unknown"


def add_count(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def processed_dataset_source_audit(dataset: Path) -> dict[str, Any]:
    data = load_dataset(dataset)
    base = dataset_base(dataset, data)
    splits: dict[str, Any] = {}
    for split in ["train", "val", "test"]:
        image_dir = base / str(data[split])
        label_dir = image_dir.parent.parent / split / "labels"
        images_by_source: dict[str, int] = {}
        damage_by_source: dict[str, int] = {}
        normal_by_source: dict[str, int] = {}
        class_boxes: dict[str, int] = {}
        for image_path in sorted(image_dir.iterdir()) if image_dir.is_dir() else []:
            if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            source = infer_source(image_path.name)
            add_count(images_by_source, source)
            label_path = label_dir / f"{image_path.stem}.txt"
            has_damage = False
            if label_path.is_file():
                for line in label_path.read_text(encoding="utf-8").splitlines():
                    parts = line.split()
                    if not parts:
                        continue
                    class_id = parts[0]
                    add_count(class_boxes, class_id)
                    if class_id == "1":
                        has_damage = True
            add_count(damage_by_source if has_damage else normal_by_source, source)

        splits[split] = {
            "imagesBySource": images_by_source,
            "imageGroupsBySource": {
                "damagePositive": damage_by_source,
                "normalOnly": normal_by_source,
            },
            "classBoxesById": class_boxes,
        }
    return splits


def metric_float(values: Any, index: int) -> float:
    return float(values[index])


def metrics_payload(metrics: Any, names: list[str]) -> dict[str, Any]:
    box = metrics.box
    per_class = []
    for class_id, class_name in enumerate(names):
        per_class.append(
            {
                "id": class_id,
                "name": class_name,
                "precision": metric_float(box.p, class_id),
                "recall": metric_float(box.r, class_id),
                "map50": metric_float(box.ap50, class_id),
                "map50_95": metric_float(box.ap, class_id),
            }
        )
    return {
        "all": {
            "precision": float(box.mp),
            "recall": float(box.mr),
            "map50": float(box.map50),
            "map50_95": float(box.map),
        },
        "classes": per_class,
    }


def source_audit(manifest: dict[str, Any], dataset: Path) -> dict[str, Any]:
    raw_audit = manifest.get("rawDuplicateSafeSourceAuditBeforeTrainSampling")
    output_audit = manifest.get("outputSourceAudit")
    processed_audit = processed_dataset_source_audit(dataset)
    if raw_audit is None and output_audit is None:
        return {
            "available": True,
            "sourceSamplesScanned": manifest.get("sourceSamplesScanned", {}),
            "sources": manifest.get("sources", {}),
            "rawDuplicateSafeSplitsBeforeTrainSampling": manifest.get(
                "rawDuplicateSafeSplitsBeforeTrainSampling",
                {},
            ),
            "processedDatasetSourceAudit": processed_audit,
            "samplingPolicy": manifest.get("samplingPolicy", {}),
            "notes": [
                "Manifest does not contain structured source audit fields.",
                "processedDatasetSourceAudit was inferred from generated file prefixes and label files.",
            ],
        }
    return {
        "available": True,
        "sourceSamplesScanned": manifest.get("sourceSamplesScanned", {}),
        "sources": manifest.get("sources", {}),
        "rawDuplicateSafeSplitsBeforeTrainSampling": manifest.get(
            "rawDuplicateSafeSplitsBeforeTrainSampling",
            {},
        ),
        "rawDuplicateSafeSourceAuditBeforeTrainSampling": raw_audit,
        "outputSourceAudit": output_audit,
        "processedDatasetSourceAudit": processed_audit,
        "samplingPolicy": manifest.get("samplingPolicy", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze an EdgeEye insulator candidate with threshold scans and source audit."
    )
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="YOLO best.pt weights to validate",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="YOLO dataset.yaml path",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional processed dataset manifest.json for source/domain audit",
    )
    parser.add_argument("--split", default="val", choices=["train", "val", "test"])
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument(
        "--conf",
        type=float,
        nargs="+",
        default=[0.5, 0.35, 0.25, 0.15],
        help="Confidence thresholds to scan",
    )
    parser.add_argument("--device", default=None)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON path",
    )
    args = parser.parse_args()

    args.weights = args.weights.expanduser().resolve()
    args.dataset = args.dataset.expanduser().resolve()
    args.output = args.output.expanduser().resolve()
    if args.manifest is None:
        args.manifest = args.dataset.parent / "manifest.json"
    else:
        args.manifest = args.manifest.expanduser().resolve()

    if not args.weights.is_file():
        raise SystemExit(f"Missing weights: {args.weights}")
    if not args.dataset.is_file():
        raise SystemExit(f"Missing dataset: {args.dataset}")

    names = load_dataset_names(args.dataset)
    model = YOLO(str(args.weights))
    scans = []
    for conf in args.conf:
        val_kwargs: dict[str, Any] = {
            "data": str(args.dataset),
            "split": args.split,
            "imgsz": args.imgsz,
            "conf": conf,
            "iou": args.iou,
            "verbose": False,
            "plots": False,
        }
        if args.device is not None:
            val_kwargs["device"] = args.device
        metrics = model.val(**val_kwargs)
        scans.append(
            {
                "conf": conf,
                "iou": args.iou,
                **metrics_payload(metrics, names),
            }
        )

    manifest = load_json(args.manifest) if args.manifest.is_file() else {}
    output = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "weights": repo_relative(args.weights),
        "dataset": repo_relative(args.dataset),
        "manifest": repo_relative(args.manifest) if args.manifest.is_file() else None,
        "split": args.split,
        "imgsz": args.imgsz,
        "thresholdScan": scans,
        "sourceAudit": source_audit(manifest, args.dataset),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote analysis to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
