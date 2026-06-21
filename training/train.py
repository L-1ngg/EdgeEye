from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the EdgeEye YOLO detector.")
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO_ROOT / "dataset" / "processed" / "edgeeye-detector-v1" / "dataset.yaml",
        help="YOLO dataset.yaml path",
    )
    parser.add_argument("--model", default="yolov8n.pt", help="Base Ultralytics model")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None, help="CUDA device id, cpu, or omitted for auto")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--project",
        type=Path,
        default=TRAINING_DIR / "runs",
        help="Ultralytics output project directory",
    )
    parser.add_argument("--name", default="edgeeye-detector-v1")
    parser.add_argument(
        "--copy-best-to",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "best.pt",
        help="Stable copy path for the best checkpoint",
    )
    args = parser.parse_args()
    args.data = args.data.expanduser().resolve()
    args.project = args.project.expanduser().resolve()
    args.copy_best_to = args.copy_best_to.expanduser().resolve()

    model = YOLO(args.model)
    train_kwargs = {
        "data": str(args.data),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "project": str(args.project),
        "name": args.name,
        "exist_ok": True,
    }
    if args.device is not None:
        train_kwargs["device"] = args.device

    result = model.train(**train_kwargs)
    best = Path(result.save_dir) / "weights" / "best.pt"
    if best.exists():
        args.copy_best_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, args.copy_best_to)
        print(f"Copied best checkpoint to {args.copy_best_to}")
    print(f"Training output: {result.save_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
