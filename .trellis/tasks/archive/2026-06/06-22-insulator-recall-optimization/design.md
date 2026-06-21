# Insulator Recall Optimization Design

## Objective

Create a recall-first successor to the current two-class insulator candidate.
The goal is to improve `insulator_surface_damage` recall without hiding the
cost in false positives or in non-representative validation data.

The updated planning assumption is that source/domain mismatch may be the main
reason the current model underperforms. The current dataset mixes sources in a
way that almost perfectly correlates image-level label state with visual style:
normal-only images are almost all substation images, while damage-positive
images are almost all Aerial/DatasetNinja images.

The optimization should proceed in two layers:

1. Measure source/domain distribution and threshold behavior of the current
   candidate.
2. Build a source-style controlled candidate if the domain confound is
   confirmed.
3. Train a new 30-epoch candidate only after the dataset policy is explicit.

## Baseline Candidate

Current candidate:

```text
models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/
dataset/processed/edgeeye-insulator-v1/
```

Independent validation metrics:

| Class | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| all | 0.81008 | 0.69179 | 0.76965 | 0.41830 |
| `insulator_normal` | 0.82434 | 0.79838 | 0.85095 | 0.52654 |
| `insulator_surface_damage` | 0.79581 | 0.58520 | 0.68835 | 0.31007 |

Baseline recall target for this task:

```text
insulator_surface_damage recall > 0.58520
```

Baseline precision guardrail:

```text
insulator_surface_damage precision >= 0.70
```

The guardrail is intentionally lower than the current `0.79581`, because recall
improvement usually costs some precision. Dropping below `0.70` would require an
explicit recall-only decision.

## Threshold Scan

Before retraining, evaluate the current `best.pt` at fixed IoU and multiple
confidence thresholds:

```text
conf = 0.50, 0.35, 0.25, 0.15
iou = 0.45
```

This is low cost and directly informs deployment settings. If a lower threshold
already meets recall goals while precision remains usable, the threshold setting
may be the best first improvement because it does not change the model package.

The scan should record:

- per-class precision, recall, mAP50, and mAP50-95
- which threshold best balances damage recall and precision
- whether expected-output generation should use the new threshold

## Source / Domain Audit

Current generated dataset source counts by image:

| Split | substation | aerial | DatasetNinja |
| --- | ---: | ---: | ---: |
| train | 3,690 | 1,686 | 200 |
| val | 691 | 151 | 10 |
| test | 697 | 143 | 13 |

Current image-level groups show the actual confound:

| Split / group | substation | aerial | DatasetNinja |
| --- | ---: | ---: | ---: |
| train damage-positive | 0 | 1,663 | 196 |
| train normal-only | 3,690 | 23 | 4 |
| val damage-positive | 0 | 145 | 10 |
| val normal-only | 691 | 6 | 0 |
| test damage-positive | 0 | 143 | 12 |
| test normal-only | 697 | 0 | 1 |

This means the model can partly solve the validation task by learning
source-specific visual style instead of damage semantics. It also means lowering
thresholds or repeating damage samples may improve metrics without improving
real cross-source generalization.

Execution should add a source/domain audit artifact that records:

- source counts by split
- source counts by damage-positive vs normal-only image groups
- sample predictions or failure cases by source
- whether normal false positives are concentrated in one source
- whether damage false negatives are concentrated in Aerial vs DatasetNinja

## Dataset Sampling Design

Current train sampling is hardcoded in `training/prepare_dataset.py`:

- max normal-only to damage-positive image ratio: `3`
- max additional copy per damage-positive image: `1`

For this pass, make these knobs explicit for the insulator variant and add a
source-control policy:

```text
--insulator-normal-cap-ratio 2
--insulator-damage-repeat 2
--insulator-source-policy domain-r1
```

Design constraints:

- Apply these knobs only to the insulator variant.
- Keep detector-v1 behavior unchanged.
- Keep val/test unresampled.
- Keep duplicate-aware grouping before splitting.
- Record source policy, knobs, and resulting counts in `manifest.json`.

Recommended `domain-r1` policy:

- It is not an aerial-only dataset.
- Keep Aerial and DatasetNinja damage-positive samples.
- Keep normal boxes that occur in Aerial/DatasetNinja images.
- Aggressively cap substation normal-only images so they act as hard negatives
  instead of dominating the normal class.
- Preserve the duplicate-safe split and source distribution evidence in the
  report.

This is not the same as simply downsampling normal or training only on Aerial.
The point is to reduce the correlation between source style and image-level
damage state while still exposing the model to substation-style normal
insulators.

Recommended new processed dataset path:

```text
dataset/processed/edgeeye-insulator-v1-domain-r1/
```

This keeps the current dataset and model artifacts intact and makes the
comparison auditable.

## Training Design

First recall-first training recipe:

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

Rationale:

- Keep `yolov8s.pt` and `imgsz=640` to avoid increasing deployment cost.
- Lower `lr0` slightly for a recall-focused follow-up run.
- Increase mosaic and add light copy-paste to expose more varied damage
  contexts.
- Remove mixup because mixed visual labels can make subtle damage localization
  less clear.
- Keep 30 epochs as requested and because the previous run peaked at the end of
  the 30-epoch window.

## Evaluation Design

Evaluate both:

1. current model under threshold scan
2. new recall-first candidate on the same candidate validation/test contract

Primary comparison:

| Metric | Baseline | Target |
| --- | ---: | ---: |
| `insulator_surface_damage` Recall | `0.58520` | materially higher |
| `insulator_surface_damage` Precision | `0.79581` | `>= 0.70` |
| `insulator_surface_damage` mAP50-95 | `0.31007` | not materially worse unless recall gain is large |

Interpretation rules:

- If recall improves but precision falls below `0.70`, keep the candidate as an
  aggressive recall experiment, not a recommended handoff.
- If the source/domain audit shows metrics are mostly driven by source style,
  prefer dataset correction over threshold-only promotion.
- If threshold scan gives a better recall/precision trade-off than retraining,
  prefer the threshold-only change only when source/domain failure analysis does
  not show an obvious style-confound problem.
- If neither improves recall, inspect false negatives and document whether the
  blocker is small targets, label inconsistency, or insufficient damage data.

## Export And Handoff

If the new candidate is worth keeping:

- copy metadata into its model package
- export ONNX with opset 11
- verify input/output contract:
  - input `images [1,3,640,640]`
  - output `output0 [1,6,8400]`
- regenerate `expected-output-v1.json` from the test split
- record SHA-256 hashes in a tracked report

Do not overwrite:

```text
models/edgeeye-insulator-v1-opt30-yolov8s-adamw/
models/edgeeye-detector-v1/
```

## Risks And Trade-Offs

- Stronger damage sampling can improve recall but may increase normal-to-damage
  false positives.
- Threshold lowering can improve recall without retraining, but it also affects
  downstream alarm volume.
- Source-style controlled training can reduce spurious source cues, but it may
  reduce normal-only diversity if too many substation images are removed.
- The damage validation set is still small, so one run is directional rather
  than conclusive.
- Keeping `imgsz=640` preserves deployment compatibility but may leave some
  small-damage misses unresolved.
