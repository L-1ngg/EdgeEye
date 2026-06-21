# EdgeEye Insulator V1 Domain-R1 Report

## Summary

This report records the source-style controlled recall candidate for the
two-class EdgeEye insulator detector.

- Date: 2026-06-22
- Previous candidate: `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/`
- Candidate dataset: `dataset/processed/edgeeye-insulator-v1-domain-r1/`
- Candidate run: `training/runs/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/`
- Candidate package: `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/`
- Status: trained for 30 epochs, independently validated, exported to ONNX,
  and kept as a versioned candidate

This candidate keeps the same two-class contract as the previous insulator-only
candidate:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |

It must not replace `edgeeye-detector-v1` automatically because that model uses
the four-class detector contract.

## Baseline Threshold Scan

The previous candidate was scanned on the duplicate-safe validation split with
fixed NMS IoU `0.45` before retraining:

```bash
cd training
uv run python analyze_insulator_candidate.py \
  --weights ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
  --dataset ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --manifest ../dataset/processed/edgeeye-insulator-v1/manifest.json \
  --split val \
  --imgsz 640 \
  --iou 0.45 \
  --conf 0.50 0.35 0.25 0.15 \
  --device 0 \
  --output ../dataset/docs/edgeeye-insulator-v1-threshold-source-audit.json
```

Per-class validation metrics:

| Conf | Class | Precision | Recall | mAP50 | mAP50-95 |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0.50 | `insulator_normal` | 0.88536 | 0.69429 | 0.66809 | 0.43731 |
| 0.50 | `insulator_surface_damage` | 0.92021 | 0.51952 | 0.50262 | 0.24052 |
| 0.35 | `insulator_normal` | 0.83034 | 0.79673 | 0.75431 | 0.47951 |
| 0.35 | `insulator_surface_damage` | 0.82553 | 0.58258 | 0.56437 | 0.26195 |
| 0.25 | `insulator_normal` | 0.79079 | 0.83295 | 0.78677 | 0.49496 |
| 0.25 | `insulator_surface_damage` | 0.78340 | 0.61562 | 0.59668 | 0.27348 |
| 0.15 | `insulator_normal` | 0.79286 | 0.83112 | 0.81696 | 0.50633 |
| 0.15 | `insulator_surface_damage` | 0.78755 | 0.61261 | 0.62677 | 0.28348 |

Lowering the confidence threshold improves damage recall from the previous
independent validation reference `0.58520` to `0.61562` at `conf=0.25`, but the
gain is small and does not address the source/domain issue below.

## Source / Domain Audit

The previous processed candidate was strongly confounded by source style and
image-level label state:

| Previous output split / group | substation | aerial | dataset-ninja |
| --- | ---: | ---: | ---: |
| train damage-positive | 0 | 1,663 | 196 |
| train normal-only | 3,690 | 23 | 4 |
| val damage-positive | 0 | 145 | 10 |
| val normal-only | 691 | 6 | 0 |
| test damage-positive | 0 | 143 | 12 |
| test normal-only | 697 | 0 | 1 |

This confirms that source and label are partially bound together: damaged
samples are almost entirely Aerial/DatasetNinja, while normal-only samples are
almost entirely substation. A model can therefore learn source style as a
shortcut instead of learning damage semantics.

The new `domain-r1` policy is not aerial-only. It keeps Aerial and DatasetNinja
damage-positive samples, keeps their normal insulator boxes, and keeps a capped
subset of substation normal-only images as hard negatives.

## Domain-R1 Dataset

Generation command:

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

Validation command:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names
```

Validation passed with:

| Split | Images | Label files | Boxes | `insulator_normal` boxes | `insulator_surface_damage` boxes |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 6,195 | 6,195 | 58,232 | 49,655 | 8,577 |
| val | 852 | 852 | 13,970 | 13,637 | 333 |
| test | 853 | 853 | 14,260 | 13,911 | 349 |
| total | 7,900 | 7,900 | 86,462 | 77,203 | 9,259 |

Raw duplicate-safe split before train sampling:

| Split | Images | Boxes | Damage-positive images | Normal-only images | Normal boxes | Damage boxes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 6,817 | 107,582 | 1,239 | 5,578 | 104,723 | 2,859 |
| val | 852 | 13,970 | 155 | 697 | 13,637 | 333 |
| test | 853 | 14,260 | 155 | 698 | 13,911 | 349 |

Domain-r1 output source audit:

| Output split / group | substation | aerial | dataset-ninja |
| --- | ---: | ---: | ---: |
| train damage-positive | 0 | 3,321 | 396 |
| train normal-only | 2,434 | 39 | 5 |
| val damage-positive | 0 | 145 | 10 |
| val normal-only | 691 | 6 | 0 |
| test damage-positive | 0 | 143 | 12 |
| test normal-only | 697 | 0 | 1 |

Train-only sampling policy:

| Policy | Value |
| --- | ---: |
| source policy | `domain-r1` |
| validation/test resampled | false |
| max normal-only to damage-positive ratio | 2 |
| original train normal-only images | 5,578 |
| kept train normal-only images | 2,478 |
| removed train normal-only images | 3,100 |
| original train damage-positive images | 1,239 |
| target train damage-positive images | 3,717 |
| added train damage repeats | 2,478 |
| max additional copies per damage image | 2 |

Validation and test remain duplicate-safe and unresampled.

## Training

Training command:

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

Training completed 30 epochs in about `1.072` hours.

Selected training metrics from `results.csv`:

| Epoch | Precision | Recall | mAP50 | mAP50-95 | Train box loss | Val box loss |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 0.81800 | 0.76437 | 0.81719 | 0.45087 | 1.17303 | 1.24811 |
| 29 | 0.82415 | 0.77645 | 0.82023 | 0.45004 | 1.12667 | 1.24394 |
| 30 | 0.83044 | 0.77113 | 0.82225 | 0.45001 | 1.11424 | 1.24118 |

The run kept improving through the final epochs, so this candidate is not
showing obvious late overfitting from the recorded losses. A longer run may
still improve it, but this task intentionally capped the first recall pass at
30 epochs.

## Candidate Validation

Independent validation command:

```bash
cd training
uv run python analyze_insulator_candidate.py \
  --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --manifest ../dataset/processed/edgeeye-insulator-v1-domain-r1/manifest.json \
  --split val \
  --imgsz 640 \
  --iou 0.45 \
  --conf 0.25 \
  --device 0 \
  --output ../dataset/docs/edgeeye-insulator-v1-domain-r1-validation-audit.json
```

Fixed-threshold validation metrics at `conf=0.25`, `iou=0.45`:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.81418 | 0.79357 | 0.75791 | 0.42163 |
| `insulator_normal` | 0.77724 | 0.81455 | 0.76295 | 0.46670 |
| `insulator_surface_damage` | 0.85113 | 0.77258 | 0.75286 | 0.37657 |

Primary comparison:

| Candidate / setting | Damage precision | Damage recall | Damage mAP50 | Damage mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| previous candidate independent reference | 0.79581 | 0.58520 | 0.68835 | 0.31007 |
| previous candidate threshold scan, `conf=0.25` | 0.78340 | 0.61562 | 0.59668 | 0.27348 |
| domain-r1 candidate, `conf=0.25` | 0.85113 | 0.77258 | 0.75286 | 0.37657 |

The domain-r1 candidate improves damage recall by `+0.18738` absolute over the
previous independent reference and by `+0.15697` over the previous candidate at
the same scanned confidence threshold. It also remains above the precision
guardrail `0.70`.

## Export And Fixture

Metadata was copied into the model package:

```bash
cp dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  dataset/processed/edgeeye-insulator-v1-domain-r1/label.names \
  dataset/processed/edgeeye-insulator-v1-domain-r1/preprocess-v1.json \
  models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/
```

ONNX export command:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt \
  --output ../models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.onnx \
  --imgsz 640 \
  --opset 11
```

ONNX verification:

```text
onnx.checker.check_model: passed
input images [1, 3, 640, 640] tensor(float)
output output0 [1, 6, 8400] tensor(float)
```

Expected-output command:

```bash
cd training
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

The generated fixture contains 5 test cases, each with non-empty detections.

## Candidate Package Hashes

| File | SHA-256 |
| --- | --- |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.pt` | `fc09697056625f0bde42f5a32a8d06543ea8031aa0b7bf2450a5d5b744a11fa8` |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/best.onnx` | `5d9ad03c7357a3adf0c99bc31edb25d6f6fb0297f3209dc8cbc5cfdf72b71721` |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/classes.json` | `40f92e0105e7706b0a51382b26e6f34cb8bf2d921f813f0bceae99f2c63f7822` |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/label.names` | `74c117699641809b88e8e06dcebeaa1f344bbc9709a2fa2abe16b26ba8e7e2c7` |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/preprocess-v1.json` | `40b7a463f2785bf8782c91ccf0028cfee2f212f0b922cb21ff53f1e0fb615333` |
| `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/expected-output-v1.json` | `dcb6cf54a0d2a71fa48e512ed80022d7758e6d4142b295b757c0af35443ce3eb` |

## Recommendation

Keep `edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw` as the stronger
insulator-only candidate and prefer it over
`edgeeye-insulator-v1-opt30-yolov8s-adamw` for the current insulator damage demo
review.

The reason is concrete: threshold tuning alone raised damage recall only to
`0.61562`, while domain-r1 raised it to `0.77258` at the same `conf=0.25` and
kept damage precision at `0.85113`.

Do not claim the source problem is fully solved. There are still no damaged
substation examples in validation/test, so this result proves a better
duplicate-safe validation trade-off, not robust substation-damage
generalization. The next highest-value work is to add or label same-source
damage and normal examples, especially aerial normal-only and substation damage,
then re-run a source-balanced validation slice.

