# EdgeEye Detector V1 Baseline Training Report

## Summary

This report records the first complete development-machine baseline training run
for `edgeeye-detector-v1`.

- Date: 2026-06-21
- Git commit before run: `8f8749c`
- Model: `yolov8n.pt`
- Dataset: `dataset/processed/edgeeye-detector-v1/dataset.yaml`
- Run output: `training/runs/edgeeye-detector-v1/`
- Handoff package: `models/edgeeye-detector-v1/`
- Atlas `.om` conversion: downstream, not run in this task

## Environment

Preflight command:

```bash
cd training
uv run python check_env.py
```

Observed environment:

- Python: 3.12.13 from `training/.venv/bin/python3`
- Ultralytics: 8.4.70
- PyTorch: 2.12.1+cu130
- CUDA available: yes
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU
- `uv`: available
- `yolo`: available from `training/.venv/bin/yolo`
- `atc`: missing locally; expected on the Atlas/CANN environment
- `kaggle`: missing locally; not needed for this training run

## Dataset

Validation command:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
```

Validation passed with:

| Split | Images | Label files | Boxes |
| --- | ---: | ---: | ---: |
| train | 8,491 | 8,491 | 112,112 |
| val | 1,030 | 1,030 | 14,985 |
| test | 890 | 890 | 18,285 |
| total | 10,411 | 10,411 | 145,382 |

Class distribution:

| Class | Boxes |
| --- | ---: |
| `insulator_normal` | 135,814 |
| `insulator_surface_damage` | 6,727 |
| `transformer_normal` | 2,754 |
| `transformer_surface_damage` | 87 |

## Smoke Gate

Smoke training completed before the baseline run:

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

Smoke export also completed:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

The smoke run proved the train-to-checkpoint-to-ONNX chain, but the smoke
checkpoint was later replaced by the full baseline checkpoint.

## Baseline Training

Baseline command:

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

Training completed 50 epochs and copied the best checkpoint to:

```text
models/edgeeye-detector-v1/best.pt
```

Key rows from `training/runs/edgeeye-detector-v1/results.csv`:

| Epoch | Precision | Recall | mAP50 | mAP50-95 |
| ---: | ---: | ---: | ---: | ---: |
| 27 | 0.79043 | 0.66237 | 0.73967 | 0.40565 |
| 30 | 0.83609 | 0.67325 | 0.76917 | 0.40178 |
| 45 | 0.79651 | 0.69465 | 0.75080 | 0.40552 |
| 50 | 0.72353 | 0.73807 | 0.72999 | 0.39159 |

Best mAP50 checkpoint row:

- Epoch: 30
- Precision: 0.83609
- Recall: 0.67325
- mAP50: 0.76917
- mAP50-95: 0.40178

Best mAP50-95 checkpoint row:

- Epoch: 27
- Precision: 0.79043
- Recall: 0.66237
- mAP50: 0.73967
- mAP50-95: 0.40565

Ultralytics selected the checkpoint copied to `models/edgeeye-detector-v1/best.pt`.
An independent validation of that checkpoint produced:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.79045 | 0.66170 | 0.73991 | 0.40442 |
| `insulator_normal` | 0.80711 | 0.63123 | 0.76059 | 0.39046 |
| `insulator_surface_damage` | 0.89617 | 0.46319 | 0.63551 | 0.27248 |
| `transformer_normal` | 0.83219 | 0.80240 | 0.85215 | 0.56016 |
| `transformer_surface_damage` | 0.62634 | 0.75000 | 0.71141 | 0.39458 |

## Export

Final ONNX export command:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-detector-v1/best.pt \
  --output ../models/edgeeye-detector-v1/best.onnx \
  --imgsz 640 \
  --opset 11
```

ONNX validation:

- Opset: 11
- Input: `images`, shape `[1, 3, 640, 640]`
- Output: `output0`, shape `[1, 8, 8400]`
- `onnx.checker.check_model`: passed

## Handoff Package

Local ignored handoff files:

| File | SHA-256 |
| --- | --- |
| `models/edgeeye-detector-v1/best.pt` | `a630cc5e8775dfcd09a44a388982bd4f93eb780fda835c59cc6abf1ae855d33d` |
| `models/edgeeye-detector-v1/best.onnx` | `b913c2a903068e2326d632b4bbd6f331061ddae7b7d2526bceb2a26275b6110b` |
| `models/edgeeye-detector-v1/classes.json` | `083eaaf19d13a56a2b23d9b74fdc7d870f9e49b3ea265b9432facecd5908f018` |
| `models/edgeeye-detector-v1/label.names` | `b415f6515477df54c5c73d22232b7014b8182374afca9e96e8680923de3b6cd3` |
| `models/edgeeye-detector-v1/preprocess-v1.json` | `40b7a463f2785bf8782c91ccf0028cfee2f212f0b922cb21ff53f1e0fb615333` |
| `models/edgeeye-detector-v1/expected-output-v1.json` | `39d976121f0c025b82a0912bbec3943fb198767a73c64c60443561f5db2792ed` |

`expected-output-v1.json` was generated from development-machine inference:

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

The generated file contains 5 test-image cases with detection counts:

```text
2, 3, 3, 4, 7
```

Use `expected-output-v1.json` as a comparison fixture after Atlas conversion.
It includes a tolerance of 4 pixels for bounding boxes and 0.05 absolute
confidence difference because CANN/runtime kernels may shift numeric output
slightly.

## Recommended Thresholds

Use the current preprocessing defaults for the first Atlas integration:

- `confidenceThreshold`: 0.25
- `nmsThreshold`: 0.45
- image size: 640 x 640
- color/layout: RGB, NCHW, normalized to `[0, 1]`

These thresholds are for integration and comparison, not final product tuning.

## Known Risks

- `transformer_surface_damage` has only 87 boxes total and only 12 boxes in the
  validation split. Its metrics can move sharply with a small number of
  detections.
- `insulator_surface_damage` validation recall is 0.46319, so missed fault boxes
  are likely in the first baseline.
- `insulator_normal` dominates the dataset. Further tuning may need sampling,
  class weighting, more balanced source data, or fault-focused evaluation.
- The model is an exportable first baseline, not a production-ready detector.

## Atlas Handoff

Give member 1 the ignored local directory:

```text
models/edgeeye-detector-v1/
```

The Atlas side should convert `best.onnx` in a CANN environment targeting the
documented Atlas SOC. After conversion, compare Atlas inference outputs against
`expected-output-v1.json` using the included tolerance.
