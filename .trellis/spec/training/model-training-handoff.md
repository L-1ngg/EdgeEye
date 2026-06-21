# Model Training Handoff Contract

## Scenario: Detector-v1 Training, Export, and Insulator-v1 Candidate Handoff

### 1. Scope / Trigger

This spec applies when changing:

- `training/train.py`
- `training/export_onnx.py`
- `training/generate_expected_output.py`
- `models/edgeeye-detector-v1/` handoff package shape
- `models/edgeeye-insulator-v1-*` candidate package shape
- detector-v1 baseline training or export documentation

The detector-v1 output is a local ignored handoff package:

```text
models/edgeeye-detector-v1/
```

The insulator-v1 optimization candidate uses a separate ignored package until
it is explicitly promoted:

```text
models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
```

Do not commit model weights, ONNX files, generated expected-output files,
training runs, raw images, or processed images.

### 2. Signatures

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

Expected-output generation:

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

### 3. Contracts

The handoff package must contain:

| File | Contract |
| --- | --- |
| `best.pt` | Stable copy of the Ultralytics best checkpoint |
| `best.onnx` | Exported from `best.pt` with `opset=11` and `imgsz=640` |
| `classes.json` | Same detector-v1 class order and contract mapping as the processed dataset |
| `label.names` | Same class order as `dataset.yaml` names |
| `preprocess-v1.json` | Input preprocessing and first integration thresholds |
| `expected-output-v1.json` | Development-machine inference fixture from at least 5 validation/test images |

ONNX contract:

- Input: `images`, shape `[1, 3, 640, 640]`
- Detector-v1 output: `output0`, shape `[1, 8, 8400]`
- Insulator-v1 two-class candidate output: `output0`, shape `[1, 6, 8400]`
- Opset: 11

For YOLOv8 detection exports, the second output dimension is `4 + class_count`.
Do not reuse the four-class parser shape for a two-class candidate.

Expected-output case contract:

- `image`: repository-relative path when possible
- `width`, `height`: positive pixel dimensions
- `detections`: non-empty array for each selected case
- each detection includes `classId`, `className`, `confidence`, pixel `bbox`,
  `deviceType`, and `faultType`

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Python dependencies missing | `check_env.py` exits non-zero and tells the user to run `uv sync` |
| Dataset class metadata disagrees | `validate_dataset.py` fails before training |
| `best.pt` missing | `export_onnx.py` exits with a clear missing-weights message |
| Expected-output source files missing | `generate_expected_output.py` exits with a clear missing-file message |
| Fewer than 5 images have detections | `generate_expected_output.py` exits non-zero; increase candidates or lower confidence |
| ONNX export has wrong opset or shape | Treat as failed export; do not hand off to Atlas |
| Ultralytics writes default root `runs/` output | Keep it ignored; do not commit generated validation plots |
| Insulator-v1 candidate overwrites `models/edgeeye-detector-v1/` | Treat as invalid promotion; restore separation and document the contract change |

### 5. Good/Base/Bad Cases

Good:

- A full baseline run completes 50 epochs, copies `best.pt`, exports `best.onnx`,
  regenerates `expected-output-v1.json`, and records metrics in a tracked report.

Base:

- A 1-epoch smoke run plus ONNX export proves the training-to-export chain before
  committing to the long baseline run.

Bad:

- Handing off a smoke checkpoint as the final baseline without recording that it
  is only a smoke model.
- Committing `models/`, `training/runs/`, `runs/`, `.pt`, `.onnx`, `.om`, or
  processed dataset files.
- Changing class order in one metadata file without changing all aligned files.

### 6. Tests Required

After training/export script changes:

- `cd training && uv run python -m py_compile train.py export_onnx.py check_env.py validate_dataset.py generate_expected_output.py`
- `cd training && uv run python check_env.py`
- dataset validation with explicit `--dataset`, `--classes`, and `--labels`
- `onnx.checker.check_model` on `models/edgeeye-detector-v1/best.onnx`
- JSON validation for `expected-output-v1.json` with at least 5 cases
- `git check-ignore -v` for generated model, run, and processed dataset paths

After a full baseline run:

- Record key metrics and known risks in a tracked report under `dataset/docs/`.
- Record SHA-256 hashes for handoff package files in the report.

After an insulator-v1 candidate run:

- Validate the candidate dataset with explicit `--dataset`, `--classes`, and
  `--labels` paths under `dataset/processed/edgeeye-insulator-v1/`.
- Export ONNX with opset 11 and verify `[1,3,640,640] -> [1,6,8400]`.
- Generate expected outputs with explicit candidate dataset metadata paths.
- Report metrics as a two-class, duplicate-safe split result and state that
  they are not directly equivalent to the previous four-class detector-v1
  baseline.

### 7. Wrong vs Correct

#### Wrong

```python
parser.add_argument("--output", default=Path("../models/edgeeye-detector-v1/best.onnx"))
```

This default depends on the current working directory and can write to the wrong
place when the script is run outside `training/`.

#### Correct

```python
TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent

parser.add_argument(
    "--output",
    type=Path,
    default=REPO_ROOT / "models" / "edgeeye-detector-v1" / "best.onnx",
)
```

Resolve script defaults from the file location, then normalize user-supplied
paths with `expanduser().resolve()`.
