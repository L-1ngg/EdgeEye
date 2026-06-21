# Insulator Recall Optimization Implementation Plan

## Status

Completed. The source-style controlled `domain-r1` candidate was generated,
trained for 30 epochs, independently validated, exported to ONNX, documented,
and checked.

## Implementation Checklist

### 1. Preflight

- [x] Read `.trellis/spec/training/dataset-preparation.md`.
- [x] Read `.trellis/spec/training/model-training-handoff.md`.
- [x] Confirm current candidate artifacts exist:
      `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/`.
- [x] Confirm current dataset exists:
      `dataset/processed/edgeeye-insulator-v1/`.
- [x] Leave unrelated dirty `.agents/` and `.trellis/workflow.md` changes
      untouched.

### 2. Threshold Scan For Current Candidate

Before changing the dataset, record the current candidate's threshold behavior.

Run validation for the existing model at:

```text
conf = 0.50, 0.35, 0.25, 0.15
iou = 0.45
```

Use the existing candidate:

```text
weights: models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt
dataset: dataset/processed/edgeeye-insulator-v1/dataset.yaml
```

Record per-class metrics in a tracked report under `dataset/docs/`.

### 3. Source / Domain Audit

- [x] Add or run a small analysis script/snippet that records source counts by:
      - split
      - damage-positive image group
      - normal-only image group
- [x] Record the current evidence:
      - train damage-positive: aerial `1663`, DatasetNinja `196`,
        substation `0`
      - train normal-only: substation `3690`, aerial `23`, DatasetNinja `4`
      - val/test show the same pattern
- [x] Inspect or summarize whether false positives/false negatives cluster by
      source.
- [x] Decide whether a threshold-only change is defensible or whether training
      needs a source-style controlled dataset.

### 4. Parameterize Insulator Sampling And Source Policy

- [x] Extend `training/prepare_dataset.py` so insulator sampling accepts:
      - `--insulator-normal-cap-ratio`
      - `--insulator-damage-repeat`
      - a source/domain policy or equivalent source cap controls
- [x] Defaults must preserve current behavior:
      - normal cap ratio `3`
      - damage repeat `1`
      - current source inclusion behavior
- [x] Apply these args only for `--variant edgeeye-insulator-v1`.
- [x] Ensure generated `manifest.json` records the configured values and
      resulting source counts.
- [x] Keep detector-v1 conversion behavior unchanged.

### 5. Generate Source-Style Controlled Dataset

Generate a separate processed dataset:

`domain-r1` is not aerial-only. It should include Aerial and DatasetNinja
damage-positive examples, keep normal boxes from those same sources, and retain
a capped subset of substation normal-only images as hard negatives.

```bash
cd training
uv run python prepare_dataset.py \
  --variant edgeeye-insulator-v1 \
  --output ../dataset/processed/edgeeye-insulator-v1-domain-r1 \
  --insulator-source-policy domain-r1 \
  --insulator-normal-cap-ratio 2 \
  --insulator-damage-repeat 2 \
  --overwrite
```

Validate:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names
```

### 6. Train Source-Style Controlled Candidate

Run the 30-epoch recipe:

```bash
cd training
uv run python train.py \
  --data ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --model yolov8s.pt \
  --epochs 30 \
  --imgsz 640 \
  --batch 8 \
  --device 0 \
  --workers 4 \
  --name edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw \
  --copy-best-to ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  --patience 12 \
  --optimizer AdamW \
  --lr0 0.002 \
  --lrf 0.01 \
  --cos-lr \
  --mosaic 0.9 \
  --close-mosaic 5 \
  --mixup 0.0 \
  --copy-paste 0.1 \
  --seed 0 \
  --deterministic
```

Record:

- duration: about `1.072` hours
- selected epoch metrics:
  - epoch 25: P `0.81800`, R `0.76437`, mAP50 `0.81719`,
    mAP50-95 `0.45087`
  - epoch 29: P `0.82415`, R `0.77645`, mAP50 `0.82023`,
    mAP50-95 `0.45004`
  - epoch 30: P `0.83044`, R `0.77113`, mAP50 `0.82225`,
    mAP50-95 `0.45001`
- independent validation at `conf=0.25`, `iou=0.45`:
  - all: P `0.81418`, R `0.79357`, mAP50 `0.75791`,
    mAP50-95 `0.42163`
  - `insulator_normal`: P `0.77724`, R `0.81455`, mAP50 `0.76295`,
    mAP50-95 `0.46670`
  - `insulator_surface_damage`: P `0.85113`, R `0.77258`,
    mAP50 `0.75286`, mAP50-95 `0.37657`

### 7. Export And Fixture

If the candidate is worth keeping:

```bash
cd training
mkdir -p ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw
cp ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names \
  ../dataset/processed/edgeeye-insulator-v1-domain-r1/preprocess-v1.json \
  ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/
uv run python export_onnx.py \
  --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  --output ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.onnx \
  --imgsz 640 \
  --opset 11
uv run python generate_expected_output.py \
  --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --classes ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/classes.json \
  --preprocess ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/preprocess-v1.json \
  --output ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/expected-output-v1.json \
  --split test \
  --min-cases 5 \
  --max-candidates 200 \
  --device 0
```

Validate ONNX:

- `onnx.checker.check_model` passes.
- onnxruntime input is `images [1,3,640,640]`.
- onnxruntime output is `output0 [1,6,8400]`.

### 8. Documentation And Report

- [x] Add a tracked report, for example:
      `dataset/docs/edgeeye-insulator-v1-domain-r1-report.md`.
- [x] Include:
      - threshold scan
      - source/domain audit and source-style confound assessment
      - dataset sampling policy and counts
      - training command
      - validation metrics
      - comparison with previous candidate
      - ONNX contract
      - expected-output summary
      - hashes for local ignored candidate package files
      - recommendation: threshold-only, promote domain-r1, or reject

Result: recommend keeping `edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw`
as the stronger insulator-only candidate for demo review. Do not treat it as a
four-class detector replacement.

### 9. Verification And Commit

Run at minimum:

```bash
cd training
uv run python -m py_compile prepare_dataset.py validate_dataset.py train.py export_onnx.py generate_expected_output.py check_env.py
uv run python check_env.py
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names
```

Also run:

```bash
git check-ignore -v \
  dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  training/runs/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/results.csv \
  models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.onnx \
  models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/expected-output-v1.json
git diff --check
python3 ./.trellis/scripts/task.py validate 06-22-insulator-recall-optimization
```

Commit only scripts, docs, specs if needed, and Trellis task artifacts. Do not
commit generated datasets, model packages, ONNX files, expected outputs, or run
outputs.

Executed verification:

- `cd training && uv run python -m py_compile prepare_dataset.py analyze_insulator_candidate.py validate_dataset.py train.py export_onnx.py generate_expected_output.py check_env.py`
- `cd training && uv run python check_env.py`
- `cd training && uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml --classes ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json --labels ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names`
- `cd training && uv run python analyze_insulator_candidate.py --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml --manifest ../dataset/processed/edgeeye-insulator-v1-domain-r1/manifest.json --split val --imgsz 640 --iou 0.45 --conf 0.25 --device 0 --output ../dataset/docs/edgeeye-insulator-v1-domain-r1-validation-audit.json`
- `cd training && uv run python export_onnx.py --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt --output ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.onnx --imgsz 640 --opset 11`
- `cd training && uv run python generate_expected_output.py --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml --classes ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/classes.json --preprocess ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/preprocess-v1.json --output ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/expected-output-v1.json --split test --min-cases 5 --max-candidates 200 --device 0`
- ONNX checker and onnxruntime shape verification: `images [1,3,640,640]` to
  `output0 [1,6,8400]`
- `git check-ignore -v` for processed dataset, training run, model package,
  ONNX, and expected-output paths
- `git diff --check`
- `python3 ./.trellis/scripts/task.py validate 06-22-insulator-recall-optimization`

## Rollback Points

- If threshold scan already meets the recall/precision target but source/domain
  audit shows severe confounding, do not promote threshold-only blindly.
- If source-style controlled sampling causes precision below `0.70`, keep the artifact as
  an experiment and do not recommend promotion.
- If ONNX export changes shape away from `[1,6,8400]`, stop before handoff and
  inspect model/class metadata.
