# EdgeEye Insulator V1 Optimization Report

## Summary

This report records the first insulator-focused optimization candidate for
EdgeEye model training.

- Date: 2026-06-21
- Candidate dataset: `dataset/processed/edgeeye-insulator-v1/`
- Candidate run: `training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/`
- Candidate package: `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/`
- Status: trained, validated, exported, and kept as a versioned candidate

This candidate intentionally changes the detector contract from four classes to
two insulator classes:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |

The candidate must not be treated as a direct replacement for
`edgeeye-detector-v1` without an explicit promotion decision.

## Baseline Reference

Previous four-class baseline independent validation:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.79045 | 0.66170 | 0.73991 | 0.40442 |
| `insulator_normal` | 0.80711 | 0.63123 | 0.76059 | 0.39046 |
| `insulator_surface_damage` | 0.89617 | 0.46319 | 0.63551 | 0.27248 |

The new candidate uses different classes, a duplicate-aware split, and
train-only resampling. Its all-class metrics are therefore not directly
equivalent to the old four-class baseline. The most useful directional
comparison is whether `insulator_surface_damage` recall and mAP50-95 improve
without making normal-insulator precision unusable.

## Dataset Generation

Generation command:

```bash
cd training
uv run python prepare_dataset.py --variant edgeeye-insulator-v1 --overwrite
```

Validation command:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1/label.names
```

Validation passed with:

| Split | Images | Label files | Boxes | `insulator_normal` boxes | `insulator_surface_damage` boxes |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 5,576 | 5,576 | 75,172 | 70,940 | 4,232 |
| val | 852 | 852 | 13,970 | 13,637 | 333 |
| test | 853 | 853 | 14,260 | 13,911 | 349 |
| total | 7,281 | 7,281 | 103,402 | 98,488 | 4,914 |

Source samples scanned:

| Source split | Samples |
| --- | ---: |
| `aerial:train` | 1,296 |
| `aerial:val` | 144 |
| `dataset-ninja:train` | 1,296 |
| `dataset-ninja:val` | 144 |
| `dataset-ninja:test` | 160 |
| `substation:agv_day` | 2,194 |
| `substation:agv_night_dark` | 180 |
| `substation:agv_night_light` | 768 |
| `substation:misc` | 3,852 |

Duplicate grouping summary:

| Item | Count |
| --- | ---: |
| scanned samples | 10,034 |
| unique samples | 8,522 |
| duplicate groups | 1,498 |
| removed duplicate samples | 1,512 |
| duplicate groups recorded in manifest | 100 |

Duplicate groups are recorded in
`dataset/processed/edgeeye-insulator-v1/manifest.json`; the recorded list is
truncated because the full group list is large.

Raw duplicate-safe split before train sampling:

| Split | Images | Boxes | Damage-positive images | Normal-only images | Normal boxes | Damage boxes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 6,817 | 107,582 | 1,239 | 5,578 | 104,723 | 2,859 |
| val | 852 | 13,970 | 155 | 697 | 13,637 | 333 |
| test | 853 | 14,260 | 155 | 698 | 13,911 | 349 |

Train-only sampling policy:

| Policy | Value |
| --- | ---: |
| max normal-only to damage-positive ratio | 3 |
| original train normal-only images | 5,578 |
| kept train normal-only images | 3,717 |
| removed train normal-only images | 1,861 |
| original train damage-positive images | 1,239 |
| target train damage-positive images | 1,859 |
| added train damage repeats | 620 |
| max additional copies per damage image | 1 |

Validation and test are duplicate-safe and unresampled.

## Training

Training command:

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
  --copy-best-to ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
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

Final training metrics:

| Row | Epoch | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| best mAP50-95 | 29 | 0.80637 | 0.69276 | 0.76935 | 0.41624 |
| best mAP50 | 30 | 0.81056 | 0.70090 | 0.77493 | 0.41619 |
| final epoch | 30 | 0.81056 | 0.70090 | 0.77493 | 0.41619 |

Independent validation metrics for the copied candidate checkpoint:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.81008 | 0.69179 | 0.76965 | 0.41830 |
| `insulator_normal` | 0.82434 | 0.79838 | 0.85095 | 0.52654 |
| `insulator_surface_damage` | 0.79581 | 0.58520 | 0.68835 | 0.31007 |

The independent validation command wrote
`models/edgeeye-insulator-v1-opt30-yolov8s-adamw/validation-metrics.json`.
The file is ignored with the rest of `models/` and is recorded here through
the report and hash table.

## Export

Candidate ONNX export command:

```bash
cd training
uv run python export_onnx.py \
  --weights ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt \
  --output ../models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.onnx \
  --imgsz 640 \
  --opset 11
```

Expected ONNX contract:

- Input: `images`, shape `[1, 3, 640, 640]`
- Output: `output0`, shape `[1, 6, 8400]`
- Opset: 11
- `onnx.checker.check_model`: passed

`[1,6,8400]` is expected for this candidate because YOLOv8 detection exports use
`4 + class_count` channels and the candidate has two classes.

Expected-output command:

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

## Candidate Package Hashes

| File | SHA-256 |
| --- | --- |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.pt` | `99782ed1383f9a6b4c52a771cb9f7dca00866a1575cc814edea8d95cb26f1530` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/best.onnx` | `42497504b2dc32cbcb41829dc2f50058953c748782e05019d8cbd3ede90a0cc1` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/classes.json` | `40f92e0105e7706b0a51382b26e6f34cb8bf2d921f813f0bceae99f2c63f7822` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/label.names` | `74c117699641809b88e8e06dcebeaa1f344bbc9709a2fa2abe16b26ba8e7e2c7` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/preprocess-v1.json` | `40b7a463f2785bf8782c91ccf0028cfee2f212f0b922cb21ff53f1e0fb615333` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/expected-output-v1.json` | `832d7d4d19f30cbde274210225ce175db68f004dd75ad36e314d664b4a3e05d6` |
| `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/validation-metrics.json` | `34d4e2173de42da3779f8fe35f8e1b7c3a7ba6f93ce24324658cb8150182ab4e` |

## Assessment

Keep this as a versioned candidate for comparison and later promotion review.
Do not replace `models/edgeeye-detector-v1/` automatically because the class
contract changed from four classes to two classes.

Directional result against the old four-class baseline:

- `insulator_surface_damage` recall improved from `0.46319` to `0.58520`.
- `insulator_surface_damage` mAP50-95 improved from `0.27248` to `0.31007`.
- `insulator_normal` mAP50-95 improved from `0.39046` to `0.52654` on the new
  duplicate-safe two-class validation split.
- Normal-insulator precision remains usable at `0.82434`.

This is a meaningful quality improvement for the insulator-only problem, but it
is not an apples-to-apples all-detector replacement. The next decision should be
whether EdgeEye wants to promote an insulator-only model contract, keep both
models side by side, or run a second pass to recover transformer coverage.

## Known Risks

- Metrics are from a new two-class, duplicate-safe split and are not directly
  interchangeable with the old four-class baseline metrics.
- Train uses documented resampling, so training distribution is intentionally
  less normal-heavy than the raw source distribution.
- Validation and test remain normal-heavy, so damage metrics are still based on
  relatively few damage boxes.
- Atlas `.om` conversion is not run locally unless the CANN `atc` environment
  is available.
