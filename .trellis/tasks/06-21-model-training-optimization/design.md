# Model Training Optimization Design

## Objective

Plan the next model-quality optimization pass. The updated priority is effect
quality over preserving the previous four-class detector contract. The preferred
candidate is now an insulator-focused detector with duplicate-aware dataset
repartitioning.

The goal is not to chase generic leaderboard gains. The first optimization pass
should target the known failure shape:

- improve `insulator_surface_damage` recall and localization quality
- reduce label/split leakage caused by duplicated insulator sources
- keep the existing four-class baseline untouched while the new candidate is
  evaluated
- keep generated data/model artifacts ignored and reproducible

## Baseline Reference

Baseline report:

```text
dataset/docs/edgeeye-detector-v1-baseline-report.md
```

Independent validation of the previous `best.pt`:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.79045 | 0.66170 | 0.73991 | 0.40442 |
| `insulator_normal` | 0.80711 | 0.63123 | 0.76059 | 0.39046 |
| `insulator_surface_damage` | 0.89617 | 0.46319 | 0.63551 | 0.27248 |
| `transformer_normal` | 0.83219 | 0.80240 | 0.85215 | 0.56016 |
| `transformer_surface_damage` | 0.62634 | 0.75000 | 0.71141 | 0.39458 |

The previous `results.csv` peaked near the requested training cap:

- best mAP50 row: epoch 30
- best mAP50-95 row: epoch 27

New scope evidence:

- Aerial and DatasetNinja source trees contain 1,440 overlapping image
  filenames, equal to the Aerial image count. Treat these as likely duplicate
  source images unless content hashes prove otherwise.
- Transformer damage has only 87 total boxes. If model effect is the priority,
  dropping transformer classes for the next candidate is more defensible than
  trying to tune around a statistically weak class.

## Updated Candidate Contract

Create a new candidate identity instead of silently changing the existing
four-class contract:

```text
edgeeye-insulator-v1
```

Classes:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |

Candidate generated paths:

```text
dataset/processed/edgeeye-insulator-v1/
training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/
models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
```

This is a contract change. Reports must state that its metrics are not directly
equivalent to the old four-class detector.

## Candidate Output Strategy

Do not overwrite the existing baseline package. Write the next run to
insulator-focused candidate paths first:

```text
training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/
models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
```

After review, the candidate can either remain versioned or be promoted into:

```text
models/edgeeye-detector-v1/
```

Promotion must be explicit because the class contract changes from four classes
to two classes.

## Dataset Rebuild Design

Build a new insulator-focused processed dataset. Do not mutate
`dataset/processed/edgeeye-detector-v1/` in place.

Source inclusion:

- Include insulator Supervisely data from Aerial/DatasetNinja after
  duplicate-aware grouping.
- Include selected substation normal-insulator classes if they improve normal
  diversity, but cap or sample them so they do not dominate the training set.
- Exclude transformer classes from this candidate.

Duplicate and split rules:

- Compute a stable image-content hash or strong duplicate key before assigning
  splits.
- Group duplicate images together so the same image cannot appear in train and
  val/test.
- Use stratified split by image-level presence of damage:
  - train: 80%
  - val: 10%
  - test: 10%
- Keep val/test representative and non-duplicated; apply any normal downsampling
  or fault oversampling only to train.
- Record split counts, class counts, duplicate groups, and sampling decisions in
  the generated manifest and tracked report.

Sampling trade-off:

- Favor better fault recall over preserving the raw normal-heavy distribution.
- Apply resampling only to train.
- Cap or downsample normal-heavy training images if they overwhelm damage
  examples.
- Lightly oversample or repeat damage-heavy training images if the resulting
  train distribution remains too normal-heavy.
- Do not oversample by copying the same rare fault images into val/test.
- Keep val/test real, duplicate-safe, and unresampled so metrics remain useful.
- If train oversampling is used, record it clearly because model behavior and
  training metrics become tied to the curated training policy.

## Training Recipe Design

### First-Pass Candidate

Start with the user-approved low-risk recipe that the current hardware can run
after adding training-script pass-through args:

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

Rationale:

- `yolov8s.pt` adds capacity over `yolov8n.pt` without jumping to a much larger
  model first.
- 30 epochs aligns with the observed baseline peak and the user's requested cap.
- Keeping `imgsz=640` preserves the current ONNX and Atlas input contract.
  Because this candidate has two classes, the exported YOLOv8 tensor shape is
  `output0 [1,6,8400]` (`4` box channels + `2` class channels), not the
  four-class baseline's `[1,8,8400]`.
- Candidate output paths prevent accidental replacement of the existing handoff.
- `AdamW`, cosine LR, moderate mosaic, and light mixup are official
  Ultralytics-supported knobs that can be passed through to `model.train()`
  without introducing a custom trainer.
- If this combined recipe underperforms, fall back to a narrower
  `yolov8s.pt`-only capacity comparison before changing the dataset.

### Script Extension Needed

Current `training/train.py` only exposes:

- `data`
- `model`
- `epochs`
- `imgsz`
- `batch`
- `device`
- `workers`
- `project`
- `name`
- `copy-best-to`

To evaluate optimization levers without hardcoding them, extend the script to
accept a small set of Ultralytics training args and pass them through to
`model.train()`:

| Argument | Purpose |
| --- | --- |
| `--patience` | Stop or select convergence behavior within the 30-epoch cap |
| `--optimizer` | Compare default auto behavior vs explicit `AdamW` or `SGD` |
| `--lr0` / `--lrf` | Bound learning-rate experiments |
| `--cos-lr` | Enable cosine LR scheduling |
| `--close-mosaic` | Stabilize final epochs by disabling mosaic late |
| `--mosaic` / `--mixup` / `--copy-paste` | Tune augmentation intensity |
| `--freeze` | Optional short transfer-learning experiment |
| `--seed` / `--deterministic` | Improve comparison repeatability |

The first implementation should avoid a custom trainer unless simple args fail.
Class-weighted loss is relevant for the extreme imbalance, but it changes
checkpoint loading expectations and should be a second-pass design if needed.
Class-balanced sampling is also a second-pass dataset task because it changes
comparison basis unless the split and manifest are documented carefully.

## Dataset Cleanup Design

Cleanup/repartition must be non-destructive. The dataset workspace currently
contains raw, processed, cache, staging, downloads, and docs directories. The
safe cleanup scope is:

- document the intended folder roles in `dataset/README.md`
- ensure generated paths are ignored by git
- create a new generated dataset directory instead of rewriting the existing
  detector-v1 output in place
- remove only empty directories or clearly stale intermediate files after
  listing them
- keep all raw archives/directories, processed detector-v1 output, and model
  handoff files unless the user explicitly approves deletion

Recommended folder roles:

| Path | Role | Cleanup rule |
| --- | --- | --- |
| `dataset/raw/` | Source datasets | Keep |
| `dataset/downloads/` | Source archives/downloads used by `prepare_dataset.py` | Keep unless duplicated and user approves |
| `dataset/processed/edgeeye-insulator-v1/` | Generated YOLO dataset for the candidate | Regenerate with script, do not hand-edit |
| `dataset/staging/` | Temporary conversion workspace | Remove only if empty or explicitly stale |
| `dataset/cache/` | Tool/cache output | Remove only if reproducible and not needed |
| `dataset/docs/` | Tracked reports | Keep and update |

## Evaluation Design

The optimized candidate should be evaluated on the same validation path and
reported against both its own held-out insulator split and the previous
insulator baseline metrics. Because train may be resampled but val/test must not
be, validation/test metrics remain the primary quality signal. A candidate is
worth promoting only if it meets
these thresholds or the user explicitly chooses a recall-first trade-off:

- `insulator_surface_damage` recall improves materially over `0.46319`
- `insulator_surface_damage` mAP50-95 improves materially over `0.27248`
- normal-insulator precision remains usable for the demo and does not collapse
  into broad false damage alarms
- mAP50-95 is reported on the new duplicate-safe split, with clear warning that
  it is not directly equivalent to the previous four-class split

Guardrails:

- do not accept a large precision collapse as a recall "win"
- inspect confusion/PR curves from the run before promotion
- regenerate ONNX and expected outputs only after picking the candidate
- do not compare the new two-class all-mAP directly against the old four-class
  all-mAP as if they measured the same task

## External References

- Ultralytics configuration docs:
  `https://docs.ultralytics.com/usage/cfg/`
- Ultralytics augmentation docs:
  `https://docs.ultralytics.com/guides/yolo-data-augmentation/`
- Ultralytics hyperparameter tuning docs:
  `https://docs.ultralytics.com/guides/hyperparameter-tuning/`
- Ultralytics fine-tuning docs:
  `https://docs.ultralytics.com/guides/finetuning-guide/`
- Ultralytics custom trainer docs:
  `https://docs.ultralytics.com/guides/custom-trainer/`

## Open Design Decisions

- Recommended default: keep `edgeeye-insulator-v1` as a separate candidate
  track beside `edgeeye-detector-v1`, because it changes the class contract and
  split policy. Promote it only with explicit handoff documentation.
