# EdgeEye Training Environment

This directory contains the local YOLO training environment for the EdgeEye
member 2 vision detector. It follows the project documentation route:

```text
dataset.yaml + label.names
  -> train.py produces best.pt
  -> export_onnx.py produces best.onnx
  -> CANN atc converts ONNX to detector-v1.om on the Atlas side
```

The first detector version uses these classes:

1. `insulator_normal`
2. `insulator_surface_damage`
3. `transformer_normal`
4. `transformer_surface_damage`

## Setup

From the repository root:

```bash
cd training
uv sync
uv run python check_env.py
```

`uv sync` creates `training/.venv/`. This environment is intentionally separate
from `backend/.venv` because PyTorch and Ultralytics are training dependencies,
not backend runtime dependencies.

## Prepare Dataset

The dataset preparation script reads the local raw datasets currently referenced
by `dataset/docs/sources.md` and writes YOLO-ready files to
`dataset/processed/edgeeye-detector-v1/`.

```bash
cd training
uv run python prepare_dataset.py --limit-per-source 50 --overwrite
uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml
```

Remove `--limit-per-source` for a full conversion once the source labels have
been reviewed. Keep `--overwrite` when regenerating the processed dataset.

Supported current local sources:

- `dataset/raw/aerial-power-infrastructure-detection-train/` Supervisely JSON.
- `insulator-defect-detection-DatasetNinja.tar` Supervisely-style JSON archive.
- `Transformer Station Detection.v1i.yolov8.zip` YOLOv8 archive.
- `dataset/raw/substation-equipment-15class/` YOLO labels, using only `Glass disc insulator`, `Porcelain pin insulator`, and `Power transformer` as normal-device examples.

## Train

Use a small dry run first:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8n.pt \
  --epochs 1 \
  --imgsz 640 \
  --batch 4 \
  --device 0
```

For the real first pass, increase `--epochs` after validating the converted
labels visually and checking the class distribution.

The current detector-v1 baseline was trained with:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 8 \
  --device 0 \
  --name edgeeye-detector-v1
```

See `dataset/docs/edgeeye-detector-v1-baseline-report.md` for the recorded
metrics, hashes, and Atlas handoff notes.

## Export ONNX

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

The Atlas `.om` conversion is expected to run on the CANN/Ascend environment
recorded in `docs/01-edge-atlas.md`.

## Generate Expected Outputs

After exporting the final checkpoint, regenerate the Atlas comparison fixture:

```bash
cd training
uv run python generate_expected_output.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/expected-output-v1.json \
  --split test \
  --min-cases 5 \
  --max-candidates 200 \
  --device 0
```

This file is generated from development-machine inference and remains ignored
under `models/`.

## Outputs

Generated files are written under ignored directories:

- `dataset/processed/edgeeye-detector-v1/`
- `models/edgeeye-detector-v1/`
- `training/runs/`
- `runs/`

Commit only the scripts, configs, and small metadata files in this directory.
