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
INSULATOR_CLASS_NAME_TO_ID = {
    "insulator_normal": 0,
    "insulator_surface_damage": 1,
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

SUBSTATION_INSULATOR_LABEL_MAP = {
    6: "insulator_normal",
    7: "insulator_normal",
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


@dataclass(frozen=True)
class InsulatorSample:
    source: str
    source_split: str
    source_id: str
    image_name: str
    image_suffix: str
    labels: tuple[str, ...]
    class_boxes: dict[str, int]
    content_sha256: str
    duplicate_keys: tuple[str, ...]
    image_path: Path | None = None
    image_bytes: bytes | None = None
    image_archive: Path | None = None
    image_member_name: str | None = None

    @property
    def has_damage(self) -> bool:
        return self.class_boxes.get("insulator_surface_damage", 0) > 0


@dataclass
class InsulatorCollection:
    samples: list[InsulatorSample] = field(default_factory=list)
    skipped_boxes: int = 0
    skipped_images: int = 0
    excluded_classes: dict[str, int] = field(default_factory=dict)
    scanned: dict[str, int] = field(default_factory=dict)

    def add_sample(self, sample: InsulatorSample) -> None:
        self.samples.append(sample)
        key = f"{sample.source}:{sample.source_split}"
        self.scanned[key] = self.scanned.get(key, 0) + 1

    def merge(self, other: "InsulatorCollection") -> None:
        self.samples.extend(other.samples)
        self.skipped_boxes += other.skipped_boxes
        self.skipped_images += other.skipped_images
        merge_counts(self.excluded_classes, other.excluded_classes)
        merge_counts(self.scanned, other.scanned)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def dataset_archive(name: str) -> Path | None:
    root = repo_root()
    return first_existing(
        [
            root / "dataset" / "downloads" / name,
            root / "dataset" / name,
            root / name,
        ]
    )


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


def label_line(
    class_name: str,
    box: tuple[float, float, float, float],
    class_name_to_id: dict[str, int] = CLASS_NAME_TO_ID,
) -> str:
    class_id = class_name_to_id[class_name]
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


def write_dataset_yaml(output: Path, class_name_to_id: dict[str, int] = CLASS_NAME_TO_ID) -> None:
    data = {
        "path": output.resolve().as_posix(),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": len(class_name_to_id),
        "names": {index: name for name, index in class_name_to_id.items()},
    }
    (output / "dataset.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def copy_metadata(output: Path) -> None:
    config_dir = repo_root() / "training" / "config"
    for name in ["classes.json", "label.names", "preprocess-v1.json"]:
        shutil.copy2(config_dir / name, output / name)


def write_insulator_metadata(output: Path) -> None:
    classes = {
        "version": "edgeeye-insulator-v1",
        "classes": [
            {
                "id": 0,
                "name": "insulator_normal",
                "type": "device",
                "deviceType": "insulator",
                "faultType": None,
            },
            {
                "id": 1,
                "name": "insulator_surface_damage",
                "type": "fault",
                "deviceType": "insulator",
                "faultType": "surface_damage",
            },
        ],
    }
    (output / "classes.json").write_text(
        json.dumps(classes, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output / "label.names").write_text(
        "\n".join(name for name, _ in sorted(INSULATOR_CLASS_NAME_TO_ID.items(), key=lambda item: item[1])) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(repo_root() / "training" / "config" / "preprocess-v1.json", output / "preprocess-v1.json")


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
    archive = dataset_archive("insulator-defect-detection-DatasetNinja.tar")
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
    archive = dataset_archive("Transformer Station Detection.v1i.yolov8.zip")
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


def safe_text(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_supervisely_labels(
    annotation: dict[str, object],
    label_map: dict[str, str],
) -> tuple[tuple[str, ...], int, dict[str, int], dict[str, int]]:
    size = annotation["size"]
    width = float(size["width"])  # type: ignore[index]
    height = float(size["height"])  # type: ignore[index]
    lines: list[str] = []
    skipped = 0
    class_boxes: dict[str, int] = {}
    excluded_classes: dict[str, int] = {}

    for obj in annotation.get("objects", []):  # type: ignore[union-attr]
        source_class_name = obj.get("classTitle", "")  # type: ignore[union-attr]
        class_name = label_map.get(source_class_name)
        if class_name is None:
            key = f"supervisely_source:{source_class_name}"
            excluded_classes[key] = excluded_classes.get(key, 0) + 1
            skipped += 1
            continue
        try:
            box = normalized_box(obj["points"]["exterior"], width, height)  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        lines.append(label_line(class_name, box, INSULATOR_CLASS_NAME_TO_ID))
        class_boxes[class_name] = class_boxes.get(class_name, 0) + 1

    return tuple(lines), skipped, class_boxes, excluded_classes


def supervisely_duplicate_keys(image_name: str, content_sha256: str) -> tuple[str, str]:
    return (f"sha256:{content_sha256}", f"supervisely-filename:{image_name.lower()}")


def collect_aerial_insulator_samples(limit_per_source: int | None) -> InsulatorCollection:
    root = repo_root() / "dataset" / "raw" / "aerial-power-infrastructure-detection-train" / "project"
    collection = InsulatorCollection()
    if not root.exists():
        return collection

    for source_split in ["train", "val"]:
        ann_dir = root / source_split / "ann"
        img_dir = root / source_split / "img"
        ann_files = limited(ann_dir.glob("*.json"), limit_per_source)
        for ann_file in tqdm(ann_files, desc=f"aerial-insulator:{source_split}"):
            image_name = ann_file.name.removesuffix(".json")
            image_path = img_dir / image_name
            if not image_path.exists():
                collection.skipped_images += 1
                continue
            annotation = json.loads(ann_file.read_text(encoding="utf-8"))
            labels, skipped, class_boxes, excluded_classes = parse_supervisely_labels(
                annotation,
                AERIAL_LABEL_MAP,
            )
            collection.skipped_boxes += skipped
            merge_counts(collection.excluded_classes, excluded_classes)
            if not labels:
                continue
            content_hash = file_sha256(image_path)
            collection.add_sample(
                InsulatorSample(
                    source="aerial",
                    source_split=source_split,
                    source_id=f"{source_split}/{image_name}",
                    image_name=image_name,
                    image_suffix=image_path.suffix.lower(),
                    image_path=image_path,
                    labels=labels,
                    class_boxes=class_boxes,
                    content_sha256=content_hash,
                    duplicate_keys=supervisely_duplicate_keys(image_name, content_hash),
                )
            )
    return collection


def collect_dataset_ninja_insulator_samples(limit_per_source: int | None) -> InsulatorCollection:
    archive = dataset_archive("insulator-defect-detection-DatasetNinja.tar")
    collection = InsulatorCollection()
    if archive is None:
        return collection

    with tarfile.open(archive) as tar:
        names = tar.getnames()
        for source_split in ["train", "val", "test"]:
            ann_names = sorted(
                name for name in names if name.startswith(f"{source_split}/ann/") and name.endswith(".json")
            )
            if limit_per_source is not None:
                ann_names = ann_names[:limit_per_source]

            for ann_name in tqdm(ann_names, desc=f"dataset-ninja-insulator:{source_split}"):
                image_name = Path(ann_name).name.removesuffix(".json")
                image_member_name = f"{source_split}/img/{image_name}"
                try:
                    annotation = json.loads(tar_member_text(tar, ann_name))
                    image_member = tar.extractfile(image_member_name)
                except (KeyError, FileNotFoundError):
                    collection.skipped_images += 1
                    continue
                if image_member is None:
                    collection.skipped_images += 1
                    continue

                image_bytes = image_member.read()
                labels, skipped, class_boxes, excluded_classes = parse_supervisely_labels(
                    annotation,
                    AERIAL_LABEL_MAP,
                )
                collection.skipped_boxes += skipped
                merge_counts(collection.excluded_classes, excluded_classes)
                if not labels:
                    continue
                content_hash = bytes_sha256(image_bytes)
                collection.add_sample(
                    InsulatorSample(
                        source="dataset-ninja",
                        source_split=source_split,
                        source_id=f"{source_split}/{image_name}",
                        image_name=image_name,
                        image_suffix=Path(image_name).suffix.lower(),
                        image_archive=archive,
                        image_member_name=image_member_name,
                        labels=labels,
                        class_boxes=class_boxes,
                        content_sha256=content_hash,
                        duplicate_keys=supervisely_duplicate_keys(image_name, content_hash),
                    )
                )
    return collection


def collect_substation_insulator_samples(limit_per_source: int | None) -> InsulatorCollection:
    root = repo_root() / "dataset" / "raw" / "substation-equipment-15class"
    collection = InsulatorCollection()
    if not root.exists():
        return collection

    eligible: list[InsulatorSample] = []
    label_files = sorted(path for path in root.rglob("*.txt") if path.name != "classes.txt")
    for label_file in tqdm(label_files, desc="substation-insulator:scan"):
        image_path = sibling_image(label_file)
        lines: list[str] = []
        file_class_boxes: dict[str, int] = {}

        for raw_line in label_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not raw_line.strip():
                continue
            parsed = parse_yolo_line(raw_line)
            if parsed is None:
                collection.skipped_boxes += 1
                continue
            source_class_id, values = parsed
            target_class_name = SUBSTATION_INSULATOR_LABEL_MAP.get(source_class_id)
            if target_class_name is None:
                source_class_name = SUBSTATION_SOURCE_CLASSES.get(source_class_id, str(source_class_id))
                key = f"substation_source_{source_class_id}:{source_class_name}"
                collection.excluded_classes[key] = collection.excluded_classes.get(key, 0) + 1
                continue

            lines.append(label_line(target_class_name, values, INSULATOR_CLASS_NAME_TO_ID))
            file_class_boxes[target_class_name] = file_class_boxes.get(target_class_name, 0) + 1

        if not lines:
            continue
        if image_path is None:
            collection.skipped_images += 1
            continue

        relative_label = label_file.relative_to(root)
        content_hash = file_sha256(image_path)
        eligible.append(
            InsulatorSample(
                source="substation",
                source_split=relative_label.parts[0] if relative_label.parts else "unknown",
                source_id=relative_label.as_posix(),
                image_name=image_path.name,
                image_suffix=image_path.suffix.lower(),
                image_path=image_path,
                labels=tuple(lines),
                class_boxes=file_class_boxes,
                content_sha256=content_hash,
                duplicate_keys=(f"sha256:{content_hash}",),
            )
        )

    for sample in eligible[:limit_per_source] if limit_per_source is not None else eligible:
        collection.add_sample(sample)
    return collection


def collect_insulator_samples(limit_per_source: int | None) -> InsulatorCollection:
    collection = InsulatorCollection()
    for partial in [
        collect_aerial_insulator_samples(limit_per_source),
        collect_dataset_ninja_insulator_samples(limit_per_source),
        collect_substation_insulator_samples(limit_per_source),
    ]:
        collection.merge(partial)
    return collection


def duplicate_group_samples(
    samples: list[InsulatorSample],
) -> tuple[list[InsulatorSample], dict[str, object]]:
    if not samples:
        return [], {
            "totalSamples": 0,
            "uniqueSamples": 0,
            "duplicateGroups": 0,
            "removedSamples": 0,
            "groups": [],
        }

    parent = list(range(len(samples)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    owner_by_key: dict[str, int] = {}
    for index, sample in enumerate(samples):
        for key in sample.duplicate_keys:
            owner = owner_by_key.get(key)
            if owner is None:
                owner_by_key[key] = index
            else:
                union(owner, index)

    grouped: dict[int, list[InsulatorSample]] = {}
    for index, sample in enumerate(samples):
        grouped.setdefault(find(index), []).append(sample)

    source_priority = {"aerial": 0, "dataset-ninja": 1, "substation": 2}

    def canonical_key(sample: InsulatorSample) -> tuple[int, int, int, str, str]:
        return (
            int(sample.has_damage),
            len(sample.labels),
            -source_priority.get(sample.source, 99),
            sample.source_split,
            sample.source_id,
        )

    def sample_manifest(sample: InsulatorSample) -> dict[str, object]:
        return {
            "source": sample.source,
            "sourceSplit": sample.source_split,
            "sourceId": sample.source_id,
            "imageName": sample.image_name,
            "contentSha256": sample.content_sha256,
            "classBoxes": sample.class_boxes,
            "hasDamage": sample.has_damage,
        }

    unique_samples: list[InsulatorSample] = []
    duplicate_groups: list[dict[str, object]] = []
    for group_index, members in enumerate(grouped.values(), start=1):
        canonical = max(members, key=canonical_key)
        unique_samples.append(canonical)
        if len(members) <= 1:
            continue
        keys = sorted({key for member in members for key in member.duplicate_keys})
        duplicate_groups.append(
            {
                "groupId": f"dup-{group_index:05d}",
                "canonical": sample_manifest(canonical),
                "members": [sample_manifest(member) for member in sorted(members, key=lambda item: item.source_id)],
                "removedSamples": len(members) - 1,
                "keys": keys,
            }
        )

    unique_samples.sort(key=lambda sample: sample.content_sha256)
    return unique_samples, {
        "totalSamples": len(samples),
        "uniqueSamples": len(unique_samples),
        "duplicateGroups": len(duplicate_groups),
        "removedSamples": len(samples) - len(unique_samples),
        "groupingKeys": ["sha256", "supervisely-filename"],
        "groupsRecorded": min(len(duplicate_groups), 100),
        "groupsTruncated": len(duplicate_groups) > 100,
        "groups": duplicate_groups[:100],
    }


def split_insulator_samples(samples: list[InsulatorSample], seed: int = 0) -> dict[str, list[InsulatorSample]]:
    splits: dict[str, list[InsulatorSample]] = {"train": [], "val": [], "test": []}

    def stable_sort_key(sample: InsulatorSample) -> str:
        return hashlib.sha256(f"{seed}:{sample.content_sha256}:{sample.source_id}".encode("utf-8")).hexdigest()

    for stratum in [True, False]:
        stratum_samples = sorted(
            [sample for sample in samples if sample.has_damage is stratum],
            key=stable_sort_key,
        )
        for index, sample in enumerate(stratum_samples):
            splits[split_for_index(index, len(stratum_samples))].append(sample)

    for split in splits:
        splits[split].sort(key=stable_sort_key)
    return splits


def apply_train_sampling(
    train_samples: list[InsulatorSample],
    seed: int = 0,
) -> tuple[list[tuple[InsulatorSample, int]], dict[str, object]]:
    def stable_sort_key(sample: InsulatorSample) -> str:
        return hashlib.sha256(f"sampling:{seed}:{sample.content_sha256}:{sample.source_id}".encode("utf-8")).hexdigest()

    damage_samples = sorted([sample for sample in train_samples if sample.has_damage], key=stable_sort_key)
    normal_only_samples = sorted([sample for sample in train_samples if not sample.has_damage], key=stable_sort_key)
    original_normal_count = len(normal_only_samples)
    normal_cap = original_normal_count
    if damage_samples:
        normal_cap = min(original_normal_count, len(damage_samples) * 3)
    kept_normal_samples = normal_only_samples[:normal_cap]
    removed_normal_samples = normal_only_samples[normal_cap:]

    target_damage_count = len(damage_samples)
    added_damage_repeats = 0
    repeated_samples: list[tuple[InsulatorSample, int]] = []
    if damage_samples and len(kept_normal_samples) > len(damage_samples) * 2:
        target_damage_count = min(len(damage_samples) * 2, (len(kept_normal_samples) + 1) // 2)
        added_damage_repeats = max(0, target_damage_count - len(damage_samples))
        for sample in damage_samples[:added_damage_repeats]:
            repeated_samples.append((sample, 1))

    originals = [(sample, 0) for sample in sorted(kept_normal_samples + damage_samples, key=stable_sort_key)]
    policy = {
        "appliesTo": ["train"],
        "valTestUnresampled": True,
        "normalOnlyCap": {
            "enabled": bool(damage_samples),
            "maxNormalOnlyToDamagePositiveRatio": 3,
            "originalTrainNormalOnlyImages": original_normal_count,
            "keptTrainNormalOnlyImages": len(kept_normal_samples),
            "removedTrainNormalOnlyImages": len(removed_normal_samples),
        },
        "damageRepeat": {
            "enabled": added_damage_repeats > 0,
            "maxAdditionalCopiesPerDamageImage": 1,
            "originalTrainDamagePositiveImages": len(damage_samples),
            "targetTrainDamagePositiveImages": target_damage_count,
            "addedTrainDamageRepeatImages": added_damage_repeats,
        },
    }
    return originals + repeated_samples, policy


def write_insulator_sample(
    output: Path,
    split: str,
    sample: InsulatorSample,
    repeat_index: int,
    tar_cache: dict[Path, tarfile.TarFile],
) -> None:
    source_stem = safe_text(f"{sample.source}_{safe_stem(Path(sample.source_id))}_{sample.content_sha256[:12]}")
    repeat_suffix = "" if repeat_index == 0 else f"_repeat{repeat_index}"
    image_suffix = sample.image_suffix if sample.image_suffix in IMAGE_SUFFIXES else ".jpg"
    target_image = output / split / "images" / f"{source_stem}{repeat_suffix}{image_suffix}"
    target_label = output / split / "labels" / f"{source_stem}{repeat_suffix}.txt"
    if sample.image_bytes is not None:
        target_image.write_bytes(sample.image_bytes)
    elif sample.image_archive is not None and sample.image_member_name is not None:
        tar = tar_cache.get(sample.image_archive)
        if tar is None:
            tar = tarfile.open(sample.image_archive)
            tar_cache[sample.image_archive] = tar
        image_member = tar.extractfile(sample.image_member_name)
        if image_member is None:
            raise FileNotFoundError(sample.image_member_name)
        target_image.write_bytes(image_member.read())
    elif sample.image_path is not None:
        shutil.copy2(sample.image_path, target_image)
    else:
        raise ValueError(f"Sample {sample.source_id} has no image payload")
    target_label.write_text("\n".join(sample.labels) + "\n", encoding="utf-8")


def build_stats_from_output(
    splits: dict[str, list[tuple[InsulatorSample, int]]],
) -> ConversionStats:
    stats = ConversionStats()
    for split, samples in splits.items():
        for sample, _repeat_index in samples:
            stats.add(
                f"{sample.source}:{sample.source_split}",
                split,
                1,
                1,
                len(sample.labels),
                0,
                0,
                sample.class_boxes,
            )
    return stats


def write_insulator_dataset(output: Path, limit_per_source: int | None) -> dict[str, object]:
    collection = collect_insulator_samples(limit_per_source)
    unique_samples, duplicate_summary = duplicate_group_samples(collection.samples)
    split_samples = split_insulator_samples(unique_samples)
    train_samples, sampling_policy = apply_train_sampling(split_samples["train"])
    output_splits = {
        "train": train_samples,
        "val": [(sample, 0) for sample in split_samples["val"]],
        "test": [(sample, 0) for sample in split_samples["test"]],
    }

    for split, samples in output_splits.items():
        tar_cache: dict[Path, tarfile.TarFile] = {}
        try:
            for sample, repeat_index in tqdm(samples, desc=f"edgeeye-insulator-v1:{split}:write"):
                write_insulator_sample(output, split, sample, repeat_index, tar_cache)
        finally:
            for tar in tar_cache.values():
                tar.close()

    total = build_stats_from_output(output_splits)
    total.skipped_boxes += collection.skipped_boxes
    total.skipped_images += collection.skipped_images
    merge_counts(total.excluded_classes, collection.excluded_classes)

    write_dataset_yaml(output, INSULATOR_CLASS_NAME_TO_ID)
    write_insulator_metadata(output)

    raw_split_counts = {
        split: {
            "images": len(samples),
            "boxes": sum(len(sample.labels) for sample in samples),
            "damagePositiveImages": sum(1 for sample in samples if sample.has_damage),
            "normalOnlyImages": sum(1 for sample in samples if not sample.has_damage),
            "classBoxes": {
                name: sum(sample.class_boxes.get(name, 0) for sample in samples)
                for name in INSULATOR_CLASS_NAME_TO_ID
            },
        }
        for split, samples in split_samples.items()
    }
    manifest = {
        "version": "edgeeye-insulator-v1",
        "images": total.images,
        "labels": total.labels,
        "boxes": total.boxes,
        "skippedBoxes": total.skipped_boxes,
        "skippedImages": total.skipped_images,
        "sources": total.sources,
        "sourceSamplesScanned": collection.scanned,
        "splits": total.splits,
        "rawDuplicateSafeSplitsBeforeTrainSampling": raw_split_counts,
        "classBoxes": {name: total.class_boxes.get(name, 0) for name in INSULATOR_CLASS_NAME_TO_ID},
        "excludedClasses": total.excluded_classes,
        "classMap": INSULATOR_CLASS_NAME_TO_ID,
        "duplicateSummary": duplicate_summary,
        "samplingPolicy": sampling_policy,
        "inventory": inventory(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_detector_dataset(output: Path, limit_per_source: int | None) -> dict[str, object]:
    total = ConversionStats()
    for stats in [
        convert_aerial(output, limit_per_source),
        convert_dataset_ninja_tar(output, limit_per_source),
        convert_transformer_zip(output, limit_per_source),
        convert_substation_equipment(output, limit_per_source),
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
    return manifest


def inventory() -> dict[str, object]:
    root = repo_root()
    dataset_root = root / "dataset"
    archives = []
    for name in [
        "24060960.zip",
        "Transformer Station Detection.v1i.yolov8.zip",
        "insulator-defect-detection-DatasetNinja.tar",
    ]:
        path = dataset_archive(name)
        if path is not None:
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
    parser = argparse.ArgumentParser(description="Prepare EdgeEye YOLO datasets.")
    parser.add_argument(
        "--variant",
        choices=["edgeeye-detector-v1", "edgeeye-insulator-v1"],
        default="edgeeye-detector-v1",
        help="Dataset contract to generate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output dataset directory. Defaults to dataset/processed/<variant> under the repo root.",
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

    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else repo_root() / "dataset" / "processed" / args.variant
    )
    reset_output(output, args.overwrite)

    if args.variant == "edgeeye-insulator-v1":
        manifest = write_insulator_dataset(output, args.limit_per_source)
    else:
        manifest = write_detector_dataset(output, args.limit_per_source)

    duplicate_summary = manifest.get("duplicateSummary")
    print(
        json.dumps(
            {
                "version": manifest["version"],
                "output": str(output),
                "images": manifest["images"],
                "labels": manifest["labels"],
                "boxes": manifest["boxes"],
                "splits": manifest["splits"],
                "classBoxes": manifest["classBoxes"],
                "duplicateSummary": {
                    key: duplicate_summary[key]
                    for key in [
                        "totalSamples",
                        "uniqueSamples",
                        "duplicateGroups",
                        "removedSamples",
                        "groupsRecorded",
                        "groupsTruncated",
                    ]
                    if isinstance(duplicate_summary, dict) and key in duplicate_summary
                }
                if isinstance(duplicate_summary, dict)
                else None,
                "samplingPolicy": manifest.get("samplingPolicy"),
                "manifest": str(output / "manifest.json"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    if int(manifest["images"]) == 0 or int(manifest["boxes"]) == 0:
        raise SystemExit("No training data was generated. Check raw dataset locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
