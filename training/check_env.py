from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_MODULES = [
    "cv2",
    "numpy",
    "onnx",
    "onnxruntime",
    "torch",
    "torchvision",
    "ultralytics",
    "yaml",
]


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable ({exc})"

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        return f"error: {message[:300]}"
    return result.stdout.strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Repository: {repo_root}")

    missing = []
    for module in REQUIRED_MODULES:
        ok = module_available(module)
        print(f"module {module}: {'ok' if ok else 'missing'}")
        if not ok:
            missing.append(module)

    if module_available("torch"):
        import torch

        print(f"torch: {torch.__version__}")
        print(f"torch.cuda.is_available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"cuda device count: {torch.cuda.device_count()}")
            print(f"cuda device 0: {torch.cuda.get_device_name(0)}")

    for tool in ["uv", "yolo", "kaggle", "atc", "nvidia-smi"]:
        location = shutil.which(tool)
        print(f"command {tool}: {location or 'missing'}")
        if tool == "nvidia-smi" and location:
            print(command_output([tool]).splitlines()[0])

    expected_paths = [
        repo_root / "dataset",
        repo_root / "dataset" / "raw",
        repo_root / "dataset" / "processed",
        repo_root / "training" / "config" / "classes.json",
        repo_root / "training" / "config" / "label.names",
        repo_root / "training" / "config" / "preprocess-v1.json",
    ]
    for path in expected_paths:
        print(f"path {path.relative_to(repo_root)}: {'ok' if path.exists() else 'missing'}")

    if missing:
        print("\nMissing Python modules. Run: cd training && uv sync")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
