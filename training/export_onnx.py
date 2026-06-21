from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an EdgeEye YOLO checkpoint to ONNX.")
    parser.add_argument(
        "--weights",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "best.pt",
        help="Path to trained best.pt",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "best.onnx",
        help="Stable ONNX output path",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=11)
    parser.add_argument("--simplify", action="store_true")
    args = parser.parse_args()
    args.weights = args.weights.expanduser().resolve()
    args.output = args.output.expanduser().resolve()

    if not args.weights.exists():
        raise SystemExit(f"Missing weights: {args.weights}")

    model = YOLO(str(args.weights))
    exported = Path(
        model.export(
            format="onnx",
            imgsz=args.imgsz,
            opset=args.opset,
            simplify=args.simplify,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if exported.resolve() != args.output.resolve():
        shutil.copy2(exported, args.output)
    print(f"ONNX export: {args.output}")
    print("Atlas atc conversion should run on the CANN environment with soc_version=Ascend310B4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
