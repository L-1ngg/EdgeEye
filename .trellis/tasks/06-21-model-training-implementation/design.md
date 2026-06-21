# Model Training Implementation Design

## Scope

This task owns the development-machine training and export handoff for
`edgeeye-detector-v1`.

It starts from the already prepared YOLO dataset:

```text
dataset/processed/edgeeye-detector-v1/
```

It produces local ignored artifacts:

```text
models/edgeeye-detector-v1/
training/runs/
```

It also produces small tracked documentation describing the baseline result and
handoff package.

Atlas `atc` conversion and `.om` validation are downstream work and stay out of
this task.

## Existing Entry Points

Environment check:

```bash
cd training
uv run python check_env.py
```

Dataset validation:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
```

Training:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 8 \
  --device 0
```

`training/train.py` writes Ultralytics outputs under `training/runs/` and copies
the best checkpoint to:

```text
models/edgeeye-detector-v1/best.pt
```

ONNX export:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

## Artifact Boundary

Ignored local artifacts:

- `dataset/processed/edgeeye-detector-v1/`
- `training/runs/`
- `models/edgeeye-detector-v1/best.pt`
- `models/edgeeye-detector-v1/best.onnx`
- `models/edgeeye-detector-v1/*.json`
- `models/edgeeye-detector-v1/*.names`

Tracked artifacts:

- planning files under `.trellis/tasks/06-21-model-training-implementation/`
- a small baseline report under `docs/` or `dataset/docs/`
- any script fixes needed to make training/export/report generation reproducible

No model binary, ONNX, OM, raw image, processed image, or training run output
should be committed.

## Handoff Package Shape

The local handoff directory should contain:

| File | Source | Purpose |
| --- | --- | --- |
| `best.pt` | `training/train.py` stable copy | Ultralytics checkpoint and retraining reference |
| `best.onnx` | `training/export_onnx.py` | Input to Atlas `atc` conversion |
| `classes.json` | copied from processed dataset or `training/config/` | Contract mapping |
| `label.names` | copied from processed dataset or `training/config/` | Class order |
| `preprocess-v1.json` | copied from processed dataset or `training/config/` | Input preprocessing and thresholds |
| `expected-output-v1.json` | generated from validation/test inference | Atlas conversion comparison fixture |

`expected-output-v1.json` should be model-output evidence, not hand-written
marketing data. It should include at least:

- model version
- source image path relative to the repository when possible
- image width and height
- `classId`
- `className`
- `confidence`
- `bbox` in pixel `[x1, y1, x2, y2]`
- `deviceType`
- `faultType`

## Baseline Training Strategy

Use a two-step approach:

1. Smoke run:
   - 1 epoch
   - small enough batch to fit the current GPU
   - proves scripts, data paths, device selection, checkpoint copy behavior, and
     ONNX export path

2. Baseline run:
   - start from `yolov8n.pt`
   - `imgsz=640`
   - `opset=11` for export
   - initial thresholds from `preprocess-v1.json`:
     - `confidenceThreshold=0.25`
     - `nmsThreshold=0.45`

The smoke run is a readiness gate only. The baseline run is required before this
task can be considered complete. The baseline run is not expected to solve all
dataset imbalance issues. Its job is to create the first exportable model and
expose concrete metrics/failure cases for the next tuning task.

## Reporting Design

The tracked report should record:

- date/time of run
- git commit or dirty-state note
- commands executed
- environment summary from `check_env.py`
- dataset path and class distribution
- model base checkpoint
- epochs, image size, batch, workers, device
- Ultralytics validation metrics that are available from the run
- produced artifact paths
- recommended thresholds
- known limitations:
  - `transformer_surface_damage` has very low sample count
  - normal insulator samples dominate
  - first baseline may favor normal-device detection over fault recall

The report should avoid claiming production readiness unless metrics support it.

## Compatibility Notes

- Keep detector-v1 class order unchanged.
- Keep `classes.json` compatible with `modelClassType` from `docs/contracts.md`.
- Keep `label.names` order identical to `dataset.yaml` names.
- Keep preprocessing aligned with `training/config/preprocess-v1.json`.
- Keep ONNX export at `opset=11` for Atlas/CANN compatibility documented in the
  project training route.

## Rollback

Because generated artifacts are ignored by git, rollback is mostly deleting or
regenerating local outputs:

```bash
rm -rf training/runs models/edgeeye-detector-v1
```

Do not delete raw or processed datasets unless the user explicitly asks.

If a script change is required and proves wrong, revert only that task-owned
change through a normal patch or git commit workflow; do not reset unrelated
user changes.
