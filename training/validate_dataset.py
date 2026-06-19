from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_dataset_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def class_names_from_yaml(data: dict[str, Any]) -> list[str]:
    names = data.get("names")
    if isinstance(names, list):
        return [str(name) for name in names]
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names)]
    raise ValueError("dataset.yaml must define names as a list or id-to-name mapping")


def read_label_names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_classes(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    classes = data.get("classes")
    if not isinstance(classes, list):
        raise ValueError("classes.json must contain a classes array")
    ordered = sorted(classes, key=lambda item: item["id"])
    return [str(item["name"]) for item in ordered]


def split_dir(base: Path, split: str, kind: str) -> Path:
    return base / split / kind


def validate_labels(
    label_dir: Path,
    image_count: int,
    class_count: int,
    names: list[str],
) -> tuple[int, int, dict[str, int]]:
    label_files = sorted(label_dir.glob("*.txt"))
    boxes = 0
    class_boxes = {name: 0 for name in names}
    invalid = []
    for label_file in label_files:
        for line_no, line in enumerate(label_file.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 5:
                invalid.append(f"{label_file}:{line_no}: expected 5 fields")
                continue
            try:
                class_id = int(parts[0])
                values = [float(value) for value in parts[1:]]
            except ValueError:
                invalid.append(f"{label_file}:{line_no}: non-numeric value")
                continue
            if not 0 <= class_id < class_count:
                invalid.append(f"{label_file}:{line_no}: class id {class_id} out of range")
            else:
                class_boxes[names[class_id]] += 1
            if any(value < 0 or value > 1 for value in values):
                invalid.append(f"{label_file}:{line_no}: box values must be normalized")
            if values[2] <= 0 or values[3] <= 0:
                invalid.append(f"{label_file}:{line_no}: width/height must be positive")
            boxes += 1
    if invalid:
        raise ValueError("\n".join(invalid[:20]))
    if image_count and len(label_files) == 0:
        raise ValueError(f"{label_dir} has images but no labels")
    return len(label_files), boxes, class_boxes


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an EdgeEye YOLO dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("../dataset/processed/edgeeye-detector-v1/dataset.yaml"),
        help="Path to dataset.yaml",
    )
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path("config/classes.json"),
        help="Path to classes.json",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("config/label.names"),
        help="Path to label.names",
    )
    args = parser.parse_args()

    dataset_path = args.dataset.resolve()
    data = load_dataset_yaml(dataset_path)
    names = class_names_from_yaml(data)
    class_count = int(data.get("nc", len(names)))
    if class_count != len(names):
        raise ValueError(f"nc={class_count} does not match names length={len(names)}")

    label_names = read_label_names(args.labels)
    classes = read_classes(args.classes)
    if names != label_names:
        raise ValueError("dataset.yaml names do not match label.names")
    if names != classes:
        raise ValueError("dataset.yaml names do not match classes.json")

    base = (dataset_path.parent / data.get("path", ".")).resolve()
    if "path" in data:
        raw_path = Path(str(data["path"]))
        base = raw_path if raw_path.is_absolute() else (dataset_path.parent / raw_path).resolve()
    else:
        base = dataset_path.parent

    total_images = 0
    total_boxes = 0
    total_class_boxes = {name: 0 for name in names}
    for split in ["train", "val", "test"]:
        image_dir = base / str(data[split])
        label_dir = image_dir.parent.parent / split / "labels"
        images = [
            path
            for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ] if image_dir.exists() else []
        label_count, boxes, class_boxes = validate_labels(label_dir, len(images), class_count, names)
        total_images += len(images)
        total_boxes += boxes
        for class_name, count in class_boxes.items():
            total_class_boxes[class_name] += count
        print(f"{split}: images={len(images)} labels={label_count} boxes={boxes}")
        print(
            "  class boxes: "
            + ", ".join(f"{class_name}={class_boxes[class_name]}" for class_name in names)
        )

    print(f"classes: {', '.join(names)}")
    print(f"total: images={total_images} boxes={total_boxes}")
    print(
        "total class boxes: "
        + ", ".join(f"{class_name}={total_class_boxes[class_name]}" for class_name in names)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
