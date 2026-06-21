# Model Training Optimization Implementation Plan

## Status

Execution in progress. The user approved prioritizing model effect, including
an insulator-focused dataset/model and revised train/val/test split if useful.
The task has been started with `task.py start`; the optimized candidate is
being generated, trained, exported, and documented without replacing the
existing four-class baseline.

## Implementation Checklist

### 1. Integrate Research

- [x] Review `.trellis/tasks/06-21-model-training-optimization/research/`
      findings.
- [x] Update `prd.md` open questions and success criteria from the research.
- [x] Adjust `design.md` if the research recommends a different first-pass
      recipe.

### 2. Prepare Training Script

- [x] Read `.trellis/spec/training/model-training-handoff.md`.
- [x] Read `.trellis/spec/training/dataset-preparation.md`.
- [x] Add or extend dataset preparation support for a new
      `edgeeye-insulator-v1` processed dataset without mutating
      `edgeeye-detector-v1`.
- [x] Keep `training/prepare_dataset.py` and `training/validate_dataset.py` as
      separate entry points; do not merge them in this task.
- [x] Implement duplicate-aware grouping before train/val/test assignment.
- [x] Support an insulator-only class contract:
      `insulator_normal`, `insulator_surface_damage`.
- [x] Extend `training/train.py` with pass-through options needed for the
      chosen 30-epoch recipe.
- [x] Keep defaults backward-compatible with the existing baseline command.
- [x] Keep output paths script-location based, not current-working-directory
      based.
- [x] Add a candidate output path in docs, not a hardcoded replacement of
      `models/edgeeye-detector-v1/`.

Candidate command shape:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --model yolov8s.pt \
  --epochs 30 \
  --imgsz 640 \
  --batch 8 \
  --device 0 \
  --workers 4 \
  --name edgeeye-insulator-v1-opt30-yolov8s-adamw \
  --copy-best-to ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt
```

Optional arguments to add if research confirms:

```bash
  --patience 12 \
  --optimizer AdamW \
  --lr0 0.003 \
  --lrf 0.01 \
  --cos-lr \
  --mosaic 0.75 \
  --close-mosaic 8 \
  --mixup 0.05 \
  --copy-paste 0.0 \
  --seed 0 \
  --deterministic
```

### 3. Dataset Folder Organization

- [x] Inspect `dataset/` with `find dataset -maxdepth 3 -type d`.
- [x] Build `dataset/processed/edgeeye-insulator-v1/` as a separate generated
      dataset.
- [x] Keep archive lookup compatible with `dataset/downloads/` and old top-level
      archive paths.
- [x] Validate that duplicates are grouped into one split and do not cross
      train/val/test.
- [x] Apply only light train-only resampling:
      - cap/downsample excessive normal-only training images
      - repeat/oversample damage-heavy training images only in train when needed
      - keep val/test real, duplicate-safe, and unresampled
- [x] Record resampling settings and resulting counts in manifest/report.
- [x] Confirm ignored generated paths with `git check-ignore -v`.
- [x] Update `dataset/README.md` with folder roles if the current explanation is
      insufficient.
- [x] List cleanup candidates and remove nothing in this pass because the
      relevant directories are source data, generated datasets, downloads,
      model packages, or training runs.
- [x] Do not delete raw datasets, processed detector-v1 data, downloads, model
      handoff files, or training runs without explicit user approval.

### 4. Preflight Validation

```bash
cd training
uv run python check_env.py
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1/label.names
uv run python -m py_compile \
  train.py export_onnx.py check_env.py validate_dataset.py \
  prepare_dataset.py generate_expected_output.py
```

### 5. Run 30-Epoch Candidate

- [x] Run the chosen 30-epoch command.
- [x] Keep run output under
      `training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/`.
- [x] Keep candidate checkpoint under
      `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt`.
- [x] Record training duration, best epoch, and key metrics.

### 6. Export Candidate

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
  --output ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.onnx \
  --imgsz 640 \
  --opset 11
```

Validate ONNX:

- opset 11
- input `images [1,3,640,640]`
- output `output0 [1,6,8400]`
- `onnx.checker.check_model` passes

Status: completed. ONNX checker passed; onnxruntime reads input
`images [1,3,640,640]` and output `output0 [1,6,8400]`.

### 7. Generate Candidate Expected Output

```bash
cd training
mkdir -p ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw
cp ../dataset/processed/edgeeye-insulator-v1/classes.json \
  ../dataset/processed/edgeeye-insulator-v1/label.names \
  ../dataset/processed/edgeeye-insulator-v1/preprocess-v1.json \
  ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
uv run python generate_expected_output.py \
  --weights ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
  --dataset ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --classes ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/classes.json \
  --preprocess ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/preprocess-v1.json \
  --output ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/expected-output-v1.json \
  --split test \
  --min-cases 5 \
  --max-candidates 200 \
  --device 0
```

If the candidate is promoted later, regenerate expected output under the final
handoff directory.

Status: completed. The generated fixture contains 5 test cases and only the two
insulator classes.

### 8. Compare and Document

- [x] Compare candidate metrics against
      `dataset/docs/edgeeye-detector-v1-baseline-report.md`.
- [x] Create or update a tracked optimization report under `dataset/docs/`.
- [x] Include command, environment, metrics, per-class table, known risks, and
      SHA-256 hashes for candidate handoff files.
- [x] Explicitly state that two-class insulator metrics are not directly
      equivalent to the old four-class detector metrics.
- [x] State whether the optimized candidate is promoted, rejected, or kept for
      further comparison.

### 9. Git and Artifact Checks

```bash
git status --short
git check-ignore -v \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.onnx \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/classes.json \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/label.names \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/preprocess-v1.json \
  models/edgeeye-insulator-v1-opt30-yolov8s-adamw/expected-output-v1.json \
  training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/results.csv \
  dataset/processed/edgeeye-insulator-v1/dataset.yaml
```

Commit only scripts, docs, specs, and Trellis artifacts. Do not commit generated
model weights, ONNX files, processed datasets, or run outputs.

## Review Gates

- [x] Research note reviewed.
- [x] `prd.md`, `design.md`, and `implement.md` are aligned.
- [x] User approves the chosen recipe before `task.py start`.
- [x] Validation commands pass or failures are documented with exact causes.

## Rollback Points

- Before training script edits: keep baseline command compatibility.
- Before deleting/cleaning dataset folders: list candidate paths and ask if not
  empty or not clearly reproducible.
- Before promoting the candidate: keep existing `models/edgeeye-detector-v1/`
  untouched because the insulator candidate changes the class contract.
