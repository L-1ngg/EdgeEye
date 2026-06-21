from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

import yaml
from tqdm import tqdm


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASS_NAME_TO_ID = {
    "insulator_normal": 0,
    "insulator_surface_damage": 1,
    "transformer_normal": 2,
    "transformer_surface_damage": 3,
}

AERIAL_LABEL_MAP = {
    "insulator": "insulator_normal",
    "broken": "insulator_surface_damage",
    "pollution-flashover": "insulator_surface_damage",
}

TRANSFORMER_LABEL_MAP = {
    0: "transformer_surface_damage",
    1: None,
    2: "transformer_normal",
}

SUBSTATION_LABEL_MAP = {
    6: "insulator_normal",
    7: "insulator_normal",
    11: "transformer_normal",
}

SUBSTATION_SOURCE_CLASSES = {
    0: "Open blade disconnect switch",
    1: "Closed blade disconnect switch",
    2: "Open tandem disconnect switch",
    3: "Closed tandem disconnect switch",
    4: "Breaker",
    5: "Fuse disconnect switch",
    6: "Glass disc insulator",
    7: "Porcelain pin insulator",
    8: "Muffle",
    9: "Lightning arrester",
    10: "Recloser",
    11: "Power transformer",
    12: "Current transformer",
    13: "Potential transformer",
    14: "Tripolar disconnect switch",
}


@dataclass
class ConversionStats:
    images: int = 0
    labels: int = 0
    boxes: int = 0
    skipped_boxes: int = 0
    skipped_images: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    splits: dict[str, dict[str, int]] = field(default_factory=dict)
    class_boxes: dict[str, int] = field(default_factory=dict)
    excluded_classes: dict[str, int] = field(default_factory=dict)

    def add(
        self,
        source: str,
        split: str,
        images: int,
        labels: int,
        boxes: int,
        skipped_boxes: int,
        skipped_images: int,
        class_boxes: dict[str, int],
        excluded_classes: dict[str, int] | None = None,
    ) -> None:
        self.images += images
        self.labels += labels
        self.boxes += boxes
        self.skipped_boxes += skipped_boxes
        self.skipped_images += skipped_images
        self.sources[source] = self.sources.get(source, 0) + images
        split_stats = self.splits.setdefault(split, {"images": 0, "labels": 0, "boxes": 0})
        split_stats["images"] += images
        split_stats["labels"] += labels
        split_stats["boxes"] += boxes
        for class_name, count in class_boxes.items():
            self.class_boxes[class_name] = self.class_boxes.get(class_name, 0) + count
        for class_name, count in (excluded_classes or {}).items():
            self.excluded_classes[class_name] = self.excluded_classes.get(class_name, 0) + count

    def merge(self, other: "ConversionStats") -> None:
        self.images += other.images
        self.labels += other.labels
        self.boxes += other.boxes
        self.skipped_boxes += other.skipped_boxes
        self.skipped_images += other.skipped_images
        for source, count in other.sources.items():
            self.sources[source] = self.sources.get(source, 0) + count
        for split, values in other.splits.items():
            split_stats = self.splits.setdefault(split, {"images": 0, "labels": 0, "boxes": 0})
            for key, value in values.items():
                split_stats[key] += value
        for class_name, count in other.class_boxes.items():
            self.class_boxes[class_name] = self.class_boxes.get(class_name, 0) + count
        for class_name, count in other.excluded_classes.items():
            self.excluded_classes[class_name] = self.excluded_classes.get(class_name, 0) + count


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def archive_metadata(path: Path) -> dict[str, str | int]:
    return {
        "path": str(path.relative_to(repo_root())),
        "sizeBytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def ensure_split_dirs(output: Path) -> None:
    for split in ["train", "val", "test"]:
        (output / split / "images").mkdir(parents=True, exist_ok=True)
        (output / split / "labels").mkdir(parents=True, exist_ok=True)


def reset_output(output: Path, overwrite: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not overwrite:
            raise SystemExit(
                f"{output} is not empty. Re-run with --overwrite to replace generated data."
            )
        shutil.rmtree(output)
    ensure_split_dirs(output)


def normalized_box(points: list[list[float]], width: float, height: float) -> tuple[float, float, float, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    x1 = max(0.0, min(min(xs), width))
    y1 = max(0.0, min(min(ys), height))
    x2 = max(0.0, min(max(xs), width))
    y2 = max(0.0, min(max(ys), height))
    box_w = x2 - x1
    box_h = y2 - y1
    if box_w <= 0 or box_h <= 0:
        raise ValueError("empty box")
    return (
        (x1 + x2) / 2 / width,
        (y1 + y2) / 2 / height,
        box_w / width,
        box_h / height,
    )


def label_line(class_name: str, box: tuple[float, float, float, float]) -> str:
    class_id = CLASS_NAME_TO_ID[class_name]
    return f"{class_id} " + " ".join(f"{value:.6f}" for value in box)


def parse_yolo_line(raw_line: str) -> tuple[int, tuple[float, float, float, float]] | None:
    parts = raw_line.split()
    if len(parts) != 5:
        return None
    try:
        class_id = int(parts[0])
        values = tuple(float(value) for value in parts[1:])
    except ValueError:
        return None
    if (
        len(values) != 4
        or any(value < 0 or value > 1 for value in values)
        or values[2] <= 0
        or values[3] <= 0
    ):
        return None
    return class_id, values


def merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, count in source.items():
        target[key] = target.get(key, 0) + count


def write_dataset_yaml(output: Path) -> None:
    data = {
        "path": output.resolve().as_posix(),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": len(CLASS_NAME_TO_ID),
        "names": {index: name for name, index in CLASS_NAME_TO_ID.items()},
    }
    (output / "dataset.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def copy_metadata(output: Path) -> None:
    config_dir = repo_root() / "training" / "config"
    for name in ["classes.json", "label.names", "preprocess-v1.json"]:
        shutil.copy2(config_dir / name, output / name)


def limited(items: Iterable[Path], limit: int | None) -> list[Path]:
    result = sorted(items)
    if limit is not None:
        return result[:limit]
    return result


def split_for_index(index: int, total: int) -> str:
    train_cutoff = int(total * 0.8)
    val_cutoff = int(total * 0.9)
    if index < train_cutoff:
        return "train"
    if index < val_cutoff:
        return "val"
    return "test"


def safe_stem(path: Path) -> str:
    stem = "_".join(path.with_suffix("").parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("_")


def sibling_image(label_file: Path) -> Path | None:
    image_dir = label_file.parent.parent
    for suffix in sorted(IMAGE_SUFFIXES):
        image_path = image_dir / f"{label_file.stem}{suffix}"
        if image_path.exists():
            return image_path
        upper_image_path = image_dir / f"{label_file.stem}{suffix.upper()}"
        if upper_image_path.exists():
            return upper_image_path
    return None


def convert_supervisely_file(
    ann_path: Path,
    image_path: Path,
    image_output: Path,
    label_output: Path,
    source_prefix: str,
    label_map: dict[str, str],
) -> tuple[bool, int, int, dict[str, int]]:
    annotation = json.loads(ann_path.read_text(encoding="utf-8"))
    size = annotation["size"]
    width = float(size["width"])
    height = float(size["height"])
    lines = []
    skipped = 0
    class_boxes: dict[str, int] = {}
    for obj in annotation.get("objects", []):
        class_name = label_map.get(obj.get("classTitle", ""))
        if class_name is None:
            skipped += 1
            continue
        try:
            box = normalized_box(obj["points"]["exterior"], width, height)
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        lines.append(label_line(class_name, box))
        class_boxes[class_name] = class_boxes.get(class_name, 0) + 1

    if not lines:
        return False, 0, skipped, class_boxes

    target_image = image_output / f"{source_prefix}_{image_path.name}"
    target_label = label_output / f"{source_prefix}_{image_path.stem}.txt"
    shutil.copy2(image_path, target_image)
    target_label.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, len(lines), skipped, class_boxes


def convert_aerial(output: Path, limit_per_source: int | None) -> ConversionStats:
    root = repo_root() / "dataset" / "raw" / "aerial-power-infrastructure-detection-train" / "project"
    stats = ConversionStats()
    if not root.exists():
        return stats

    for source_split, split in [("train", "train"), ("val", "val")]:
        ann_dir = root / source_split / "ann"
        img_dir = root / source_split / "img"
        ann_files = limited(ann_dir.glob("*.json"), limit_per_source)
        images = labels = boxes = skipped_boxes = skipped_images = 0
        class_boxes: dict[str, int] = {}
        for ann_file in tqdm(ann_files, desc=f"aerial:{source_split}"):
            image_name = ann_file.name.removesuffix(".json")
            image_path = img_dir / image_name
            if not image_path.exists():
                skipped_images += 1
                continue
            ok, box_count, skipped_count, file_class_boxes = convert_supervisely_file(
                ann_file,
                image_path,
                output / split / "images",
                output / split / "labels",
                f"aerial_{source_split}",
                AERIAL_LABEL_MAP,
            )
            skipped_boxes += skipped_count
            if ok:
                images += 1
                labels += 1
                boxes += box_count
                for class_name, count in file_class_boxes.items():
                    class_boxes[class_name] = class_boxes.get(class_name, 0) + count
        stats.add(
            f"aerial:{source_split}",
            split,
            images,
            labels,
            boxes,
            skipped_boxes,
            skipped_images,
            class_boxes,
        )
    return stats


def tar_member_text(tar: tarfile.TarFile, name: str) -> str:
    member = tar.extractfile(name)
    if member is None:
        raise FileNotFoundError(name)
    return member.read().decode("utf-8")


def convert_dataset_ninja_tar(output: Path, limit_per_source: int | None) -> ConversionStats:
    archive = first_existing(
        [
            repo_root() / "dataset" / "insulator-defect-detection-DatasetNinja.tar",
            repo_root() / "insulator-defect-detection-DatasetNinja.tar",
        ]
    )
    stats = ConversionStats()
    if archive is None:
        return stats

    with tarfile.open(archive) as tar:
        names = tar.getnames()
        for source_split, split in [("train", "train"), ("val", "val"), ("test", "test")]:
            ann_names = sorted(
                name for name in names if name.startswith(f"{source_split}/ann/") and name.endswith(".json")
            )
            if limit_per_source is not None:
                ann_names = ann_names[:limit_per_source]

            images = labels = boxes = skipped_boxes = skipped_images = 0
            class_boxes: dict[str, int] = {}
            for ann_name in tqdm(ann_names, desc=f"dataset-ninja:{source_split}"):
                image_name = Path(ann_name).name.removesuffix(".json")
                image_member_name = f"{source_split}/img/{image_name}"
                try:
                    annotation = json.loads(tar_member_text(tar, ann_name))
                    image_member = tar.extractfile(image_member_name)
                except (KeyError, FileNotFoundError):
                    skipped_images += 1
                    continue
                if image_member is None:
                    skipped_images += 1
                    continue

                size = annotation["size"]
                width = float(size["width"])
                height = float(size["height"])
                lines = []
                for obj in annotation.get("objects", []):
                    class_name = AERIAL_LABEL_MAP.get(obj.get("classTitle", ""))
                    if class_name is None:
                        skipped_boxes += 1
                        continue
                    try:
                        box = normalized_box(obj["points"]["exterior"], width, height)
                    except (KeyError, TypeError, ValueError):
                        skipped_boxes += 1
                        continue
                    lines.append(label_line(class_name, box))
                    class_boxes[class_name] = class_boxes.get(class_name, 0) + 1
                if not lines:
                    continue

                target_image = output / split / "images" / f"datasetninja_{source_split}_{image_name}"
                target_label = output / split / "labels" / f"datasetninja_{source_split}_{Path(image_name).stem}.txt"
                target_image.write_bytes(image_member.read())
                target_label.write_text("\n".join(lines) + "\n", encoding="utf-8")
                images += 1
                labels += 1
                boxes += len(lines)
            stats.add(
                f"dataset-ninja:{source_split}",
                split,
                images,
                labels,
                boxes,
                skipped_boxes,
                skipped_images,
                class_boxes,
            )
    return stats


def convert_transformer_zip(output: Path, limit_per_source: int | None) -> ConversionStats:
    archive = first_existing(
        [
            repo_root() / "dataset" / "Transformer Station Detection.v1i.yolov8.zip",
            repo_root() / "Transformer Station Detection.v1i.yolov8.zip",
        ]
    )
    stats = ConversionStats()
    if archive is None:
        return stats

    with ZipFile(archive) as zip_file:
        names = set(zip_file.namelist())
        for source_split, split in [("train", "train"), ("valid", "val"), ("test", "test")]:
            image_names = sorted(
                name
                for name in names
                if name.startswith(f"{source_split}/images/")
                and Path(name).suffix.lower() in IMAGE_SUFFIXES
            )
            if limit_per_source is not None:
                image_names = image_names[:limit_per_source]
            images = labels = boxes = skipped_boxes = skipped_images = 0
            class_boxes: dict[str, int] = {}
            excluded_classes: dict[str, int] = {}
            for image_name in tqdm(image_names, desc=f"transformer:{source_split}"):
                image_stem = Path(image_name).stem
                label_name = f"{source_split}/labels/{image_stem}.txt"
                if label_name not in names:
                    skipped_images += 1
                    continue
                lines = []
                for raw_line in zip_file.read(label_name).decode("utf-8").splitlines():
                    if not raw_line.strip():
                        continue
                    parsed = parse_yolo_line(raw_line)
                    if parsed is None:
                        skipped_boxes += 1
                        continue
                    source_class_id, values = parsed
                    target_class_name = TRANSFORMER_LABEL_MAP.get(source_class_id)
                    if target_class_name is None:
                        excluded_classes[f"transformer_source_{source_class_id}"] = (
                            excluded_classes.get(f"transformer_source_{source_class_id}", 0) + 1
                        )
                        skipped_boxes += 1
                        continue
                    lines.append(label_line(target_class_name, values))
                    class_boxes[target_class_name] = class_boxes.get(target_class_name, 0) + 1
                if not lines:
                    continue

                target_image = output / split / "images" / f"transformer_{source_split}_{Path(image_name).name}"
                target_label = output / split / "labels" / f"transformer_{source_split}_{image_stem}.txt"
                target_image.write_bytes(zip_file.read(image_name))
                target_label.write_text("\n".join(lines) + "\n", encoding="utf-8")
                images += 1
                labels += 1
                boxes += len(lines)
            stats.add(
                f"transformer:{source_split}",
                split,
                images,
                labels,
                boxes,
                skipped_boxes,
                skipped_images,
                class_boxes,
                excluded_classes,
            )
    return stats


def convert_substation_equipment(output: Path, limit_per_source: int | None) -> ConversionStats:
    root = repo_root() / "dataset" / "raw" / "substation-equipment-15class"
    stats = ConversionStats()
    if not root.exists():
        return stats

    eligible: list[tuple[Path, Path, list[str], int, dict[str, int]]] = []
    skipped_boxes = 0
    skipped_images = 0
    missing_image_candidates = 0
    excluded_classes: dict[str, int] = {}

    label_files = sorted(path for path in root.rglob("*.txt") if path.name != "classes.txt")
    for label_file in tqdm(label_files, desc="substation:scan"):
        image_path = sibling_image(label_file)
        lines = []
        file_class_boxes: dict[str, int] = {}

        for raw_line in label_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            parsed = parse_yolo_line(raw_line)
            if parsed is None:
                skipped_boxes += 1
                continue
            source_class_id, values = parsed

            target_class_name = SUBSTATION_LABEL_MAP.get(source_class_id)
            if target_class_name is None:
                source_class_name = SUBSTATION_SOURCE_CLASSES.get(source_class_id, str(source_class_id))
                key = f"substation_source_{source_class_id}:{source_class_name}"
                excluded_classes[key] = excluded_classes.get(key, 0) + 1
                continue

            lines.append(label_line(target_class_name, values))
            file_class_boxes[target_class_name] = file_class_boxes.get(target_class_name, 0) + 1

        if not lines:
            continue

        if image_path is None:
            missing_image_candidates += 1
            continue

        eligible.append(
            (
                label_file,
                image_path,
                lines,
                len(lines),
                file_class_boxes,
            )
        )

    eligible = eligible[:limit_per_source] if limit_per_source is not None else eligible
    skipped_images = missing_image_candidates
    total = len(eligible)
    split_stats: dict[str, ConversionStats] = {split: ConversionStats() for split in ["train", "val", "test"]}

    for index, (
        label_file,
        image_path,
        lines,
        box_count,
        file_class_boxes,
    ) in enumerate(tqdm(eligible, desc="substation:write")):
        split = split_for_index(index, total)
        relative_stem = safe_stem(label_file.relative_to(root))
        target_image = output / split / "images" / f"substation_{relative_stem}{image_path.suffix.lower()}"
        target_label = output / split / "labels" / f"substation_{relative_stem}.txt"
        shutil.copy2(image_path, target_image)
        target_label.write_text("\n".join(lines) + "\n", encoding="utf-8")
        split_stats[split].add(
            f"substation:{split}",
            split,
            1,
            1,
            box_count,
            0,
            0,
            file_class_boxes,
        )

    for split in ["train", "val", "test"]:
        stats.merge(split_stats[split])
    stats.skipped_boxes += skipped_boxes
    stats.skipped_images += skipped_images
    merge_counts(stats.excluded_classes, excluded_classes)
    return stats


def inventory() -> dict[str, object]:
    root = repo_root()
    dataset_root = root / "dataset"
    archives = []
    for path in [
        dataset_root / "24060960.zip",
        dataset_root / "Transformer Station Detection.v1i.yolov8.zip",
        dataset_root / "insulator-defect-detection-DatasetNinja.tar",
    ]:
        if path.exists():
            archives.append(archive_metadata(path))

    aerial_root = dataset_root / "raw" / "aerial-power-infrastructure-detection-train" / "project"
    raw_dirs: dict[str, object] = {}
    if aerial_root.exists():
        raw_dirs["aerial-power-infrastructure-detection-train"] = {
            "path": str(aerial_root.relative_to(root)),
            "trainImages": len(list((aerial_root / "train" / "img").glob("*"))),
            "trainAnnotations": len(list((aerial_root / "train" / "ann").glob("*.json"))),
            "valImages": len(list((aerial_root / "val" / "img").glob("*"))),
            "valAnnotations": len(list((aerial_root / "val" / "ann").glob("*.json"))),
            "format": "Supervisely JSON",
        }

    substation_root = dataset_root / "raw" / "substation-equipment-15class"
    if substation_root.exists():
        raw_dirs["substation-equipment-15class"] = {
            "path": str(substation_root.relative_to(root)),
            "images": len(
                [
                    path
                    for path in substation_root.rglob("*")
                    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
                ]
            ),
            "labels": len(
                [
                    path
                    for path in substation_root.rglob("*.txt")
                    if path.name != "classes.txt"
                ]
            ),
            "classes": len(
                [
                    line
                    for line in (substation_root / "classes.txt").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            )
            if (substation_root / "classes.txt").exists()
            else 0,
            "format": "YOLO",
        }

    return {
        "datasetRoot": str(dataset_root.relative_to(root)),
        "archives": archives,
        "rawDirectories": raw_dirs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the EdgeEye detector-v1 YOLO dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../dataset/processed/edgeeye-detector-v1"),
        help="Output dataset directory",
    )
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=None,
        help="Optional per-source limit for smoke conversions",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output directory if it already contains files",
    )
    args = parser.parse_args()

    output = args.output.resolve()
    reset_output(output, args.overwrite)

    total = ConversionStats()
    for stats in [
        convert_aerial(output, args.limit_per_source),
        convert_dataset_ninja_tar(output, args.limit_per_source),
        convert_transformer_zip(output, args.limit_per_source),
        convert_substation_equipment(output, args.limit_per_source),
    ]:
        total.merge(stats)

    write_dataset_yaml(output)
    copy_metadata(output)

    manifest = {
        "version": "edgeeye-detector-v1",
        "images": total.images,
        "labels": total.labels,
        "boxes": total.boxes,
        "skippedBoxes": total.skipped_boxes,
        "skippedImages": total.skipped_images,
        "sources": total.sources,
        "splits": total.splits,
        "classBoxes": {name: total.class_boxes.get(name, 0) for name in CLASS_NAME_TO_ID},
        "excludedClasses": total.excluded_classes,
        "classMap": CLASS_NAME_TO_ID,
        "inventory": inventory(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if total.images == 0 or total.boxes == 0:
        raise SystemExit("No training data was generated. Check raw dataset locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
