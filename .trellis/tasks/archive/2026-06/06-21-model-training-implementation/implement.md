# Model Training Implementation Plan

## Execution Checklist

1. Confirm task context.
   - Read `prd.md`, `design.md`, and this file.
   - Load training specs before code changes.
   - Run `python3 ./.trellis/scripts/task.py start 06-21-model-training-implementation` only after user review approval.

2. Preflight current environment and dataset.
   - `cd training && uv run python check_env.py`
   - `cd training && uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml --classes ../dataset/processed/edgeeye-detector-v1/classes.json --labels ../dataset/processed/edgeeye-detector-v1/label.names`
   - Record any CUDA/device limitation before training.

3. Run a smoke training pass and export check.
   - Use `yolov8n.pt`, `epochs=1`, `imgsz=640`.
   - Prefer `--device 0` when CUDA is available; fall back to CPU only if the user accepts slower execution or GPU is unavailable.
   - Use a conservative batch if memory is uncertain.
   - Confirm `models/edgeeye-detector-v1/best.pt` is written.
   - Export that smoke checkpoint to ONNX to prove the train-to-export chain.

4. Run the first baseline training pass.
   - Use the current full processed dataset.
   - Start with:

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

   - If GPU memory fails, retry with lower batch and document the final command.
   - If runtime prevents completion, preserve the failed command/output summary and document the next runnable command.
   - Do not archive this task as complete until the baseline run finishes and metrics are recorded.

5. Export ONNX.

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

6. Assemble local handoff files.
   - Copy `classes.json`, `label.names`, and `preprocess-v1.json` into `models/edgeeye-detector-v1/`.
   - Generate or assemble `expected-output-v1.json` from at least 5 validation/test image inferences.
   - Keep all handoff artifacts ignored by git.

7. Write tracked evaluation/handoff report.
   - Include commands, environment, dataset summary, metrics, thresholds, artifacts, and known risks.
   - Explicitly state that Atlas `.om` conversion is downstream.

8. Final validation.
   - Confirm `best.pt` and `best.onnx` exist locally.
   - Confirm no ignored large artifacts are staged or tracked.
   - Run `git status --short`.
   - Run `python -m py_compile` on changed training scripts if any script was changed.

## Validation Commands

Required preflight:

```bash
cd training
uv run python check_env.py
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
```

Smoke training:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --model yolov8n.pt \
  --epochs 1 \
  --imgsz 640 \
  --batch 4 \
  --device 0 \
  --name edgeeye-detector-v1-smoke
```

Baseline training:

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

ONNX export:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

If training scripts are changed:

```bash
python -m py_compile training/train.py training/export_onnx.py training/check_env.py training/validate_dataset.py
```

## Risk Points

- Full baseline training may exceed the interactive session length.
- GPU memory may require lowering batch size.
- CPU fallback may be too slow for full baseline training.
- `transformer_surface_damage` metrics may be weak due to only 87 boxes.
- A smoke-trained `best.pt` is useful for export validation but should not be presented as a real baseline model unless clearly labeled.

## User-Confirmed Training Acceptance Policy

Confirmed on 2026-06-21:

- Final completion requires the full baseline training run to finish and metrics
  to be recorded.
- The immediate next step is only to verify the chain with `check_env.py`,
  dataset validation, 1 epoch smoke training, and ONNX export.
- A successful smoke chain does not complete or archive the task; it only clears
  the way for the longer baseline run.
