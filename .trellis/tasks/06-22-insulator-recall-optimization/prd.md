# 绝缘子模型召回率优化

## Goal

Improve `insulator_surface_damage` recall for the existing two-class
insulator-focused detector while keeping false damage alarms within a usable
range for the EdgeEye demo.

The likely root issue is not only class imbalance. Current evidence suggests a
source/style confound: normal-only images are almost entirely from the
substation source, while damage-positive images are almost entirely from
Aerial/DatasetNinja. The next execution pass must diagnose and reduce that
source/domain mismatch before amplifying train resampling.

This task should produce a new versioned candidate instead of overwriting the
previous `edgeeye-insulator-v1-opt30-yolov8s-adamw` package.

## Confirmed Facts

- The current insulator-focused candidate was trained on
  `dataset/processed/edgeeye-insulator-v1/dataset.yaml` for 30 epochs with
  `yolov8s.pt`.
- Current candidate path:
  `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/`.
- Current candidate run path:
  `training/runs/edgeeye-insulator-v1-opt30-yolov8s-adamw/`.
- Current independent validation metrics:
  - all: Precision `0.81008`, Recall `0.69179`, mAP50 `0.76965`,
    mAP50-95 `0.41830`
  - `insulator_normal`: Precision `0.82434`, Recall `0.79838`,
    mAP50 `0.85095`, mAP50-95 `0.52654`
  - `insulator_surface_damage`: Precision `0.79581`, Recall `0.58520`,
    mAP50 `0.68835`, mAP50-95 `0.31007`
- Current generated dataset counts:
  - train: 5,576 images, 75,172 boxes, 4,232 damage boxes
  - val: 852 images, 13,970 boxes, 333 damage boxes
  - test: 853 images, 14,260 boxes, 349 damage boxes
- Current train-only sampling policy is hardcoded:
  - normal-only cap: max `3:1` normal-only images to damage-positive images
  - damage-positive repeat: max one additional copy per damage-positive image
  - validation and test remain unresampled
- Current preprocess metadata uses:
  - `confidenceThreshold: 0.25`
  - `nmsThreshold: 0.45`
- User approved a recall-improvement pass on 2026-06-22.
- User identified a likely data-source/style mismatch on 2026-06-22.
- Current generated dataset source distribution confirms a class/source
  confound:
  - train images by source: substation `3690`, aerial `1686`,
    DatasetNinja `200`
  - train damage-positive images by source: aerial `1663`,
    DatasetNinja `196`, substation `0`
  - train normal-only images by source: substation `3690`, aerial `23`,
    DatasetNinja `4`
  - val damage-positive images by source: aerial `145`, DatasetNinja `10`,
    substation `0`
  - val normal-only images by source: substation `691`, aerial `6`
  - test damage-positive images by source: aerial `143`, DatasetNinja `12`,
    substation `0`
  - test normal-only images by source: substation `697`, DatasetNinja `1`

## Requirements

- Keep the task focused on the two-class insulator detector:
  - `insulator_normal`
  - `insulator_surface_damage`
- Optimize for higher `insulator_surface_damage` recall.
- Do not make validation/test metrics artificially better:
  - no val/test resampling
  - no duplicate leakage across train/val/test
  - keep validation/test duplicate-safe and real
- Add a threshold-scan step for the current model before training another
  candidate, so the first recall gain can come from inference configuration if
  possible.
- Add a source/domain audit before retraining:
  - source distribution by split
  - source distribution by image-level damage presence
  - per-source failure inspection or metrics when feasible
  - explicit assessment of whether the model is learning source style instead
    of damage semantics
- Prioritize reducing source/style confounding over blindly increasing
  damage-positive repetition.
- Add configurable train-only sampling knobs for the insulator dataset builder,
  rather than changing hardcoded constants silently.
- First candidate should be source-style controlled, not merely recall-weighted.
  `domain-r1` is not an aerial-only dataset. It should keep Aerial and
  DatasetNinja damage-positive examples, keep their normal insulator boxes, and
  retain a capped subset of substation normal-only images as hard negatives.
  Candidate policies to evaluate during execution:
  - exclude or cap substation normal-only images aggressively
  - keep Aerial/DatasetNinja normal boxes from damage-positive images
  - optionally create a source-balanced validation report without modifying the
    real validation/test split
  - use substation normal-only images as hard negatives only after measuring
    whether they hurt cross-source generalization
- First recall-first training cap remains 30 epochs.
- First recall-first training recipe should stay deployment-compatible with
  `imgsz=640` and YOLOv8s unless evidence shows small-object misses dominate.
- Store new generated data/model artifacts under distinct versioned paths, for
  example:
  - `dataset/processed/edgeeye-insulator-v1-domain-r1/`
  - `training/runs/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/`
  - `models/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw/`
- Preserve the current candidate under
  `models/edgeeye-insulator-v1-opt30-yolov8s-adamw/`.
- Keep generated weights, ONNX files, expected outputs, training runs, raw
  images, and processed images ignored by git.

## Acceptance Criteria

- [ ] `prd.md`, `design.md`, and `implement.md` exist and describe the
      recall-first scope before execution starts.
- [ ] Current-model threshold scan records per-class validation metrics for at
      least `conf=0.50`, `0.35`, `0.25`, and `0.15` with fixed NMS IoU.
- [ ] A source/domain audit records source distribution by split and by
      damage-positive vs normal-only image groups.
- [ ] The report explicitly states whether the previous dataset is confounded
      by source style and class label.
- [ ] `training/prepare_dataset.py` supports configurable insulator train-only
      sampling/source-control knobs without changing detector-v1 defaults.
- [ ] A source-style controlled processed dataset is generated and validated
      with duplicate-aware split and unresampled val/test.
- [ ] The generated manifest/report records source policy, normal cap ratio,
      and damage repeat settings.
- [ ] A 30-epoch source-style controlled candidate is trained with a new
      run/model name.
- [ ] Candidate validation compares against the current candidate:
      - target: `insulator_surface_damage` recall improves materially over
        `0.58520`
      - guardrail: `insulator_surface_damage` precision should remain at or
        above `0.70` unless the user explicitly accepts a more aggressive
        recall-only trade-off
      - guardrail: normal-insulator precision should not collapse into broad
        false damage positives
- [ ] Candidate ONNX export is verified as `[1,3,640,640] -> [1,6,8400]`
      unless a later explicit decision changes `imgsz`.
- [ ] Candidate expected output is regenerated from test images with explicit
      candidate metadata.
- [ ] A tracked report under `dataset/docs/` records commands, threshold-scan
      results, dataset policy, validation metrics, hashes, and promotion
      recommendation.

## Out of Scope

- Atlas `.om` conversion unless the local CANN/Ascend `atc` environment is
  available.
- Replacing or deleting the previous insulator candidate.
- Replacing `edgeeye-detector-v1`.
- Adding transformer classes back into this candidate.
- Changing the model input size away from 640 in the first pass.
- Custom loss functions or a custom Ultralytics trainer.
- Manual relabeling at scale; this task may document label-quality findings but
  should not depend on large annotation work before the first recall-first run.

## Open Questions

- None blocking planning.

## Decisions

- On 2026-06-22, the user approved prioritizing the `domain-r1`
  source-style-controlled dataset over pure recall-first resampling.
- `domain-r1` is not aerial-only. It keeps Aerial and DatasetNinja
  damage-positive examples, keeps their normal insulator boxes, and retains a
  capped subset of substation normal-only images as hard negatives.
- Trade-off accepted for planning: source control may reduce normal-only
  diversity, so precision must remain guarded while recall improves.
