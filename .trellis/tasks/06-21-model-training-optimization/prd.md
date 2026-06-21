# 模型训练结果优化

## Goal

Improve model quality after the first YOLOv8n baseline. If needed, prioritize
an insulator-focused detector over the previous four-class detector and allow a
reviewed dataset rebuild plus train/val/test repartition.

This task starts in planning/research. It must not replace the previous
baseline handoff until an optimized run is trained, evaluated, exported, and
explicitly documented as the new candidate.

## Confirmed Facts

- The previous baseline task completed a 50-epoch `yolov8n.pt` training run on
  `dataset/processed/edgeeye-detector-v1/dataset.yaml`.
- The baseline handoff package is local and ignored under
  `models/edgeeye-detector-v1/`.
- Baseline validation metrics recorded in
  `dataset/docs/edgeeye-detector-v1-baseline-report.md`:
  - all: Precision `0.79045`, Recall `0.66170`, mAP50 `0.73991`,
    mAP50-95 `0.40442`
  - `insulator_surface_damage`: Recall `0.46319`, mAP50-95 `0.27248`
  - `transformer_surface_damage`: 87 boxes total, 12 boxes in validation
- `results.csv` recorded best mAP50 around epoch 30 and best mAP50-95 around
  epoch 27, so the next run should be capped at 30 epochs unless research
  provides a strong reason otherwise.
- Class imbalance is the dominant known dataset risk:
  `insulator_normal` has 135,814 boxes while `transformer_surface_damage` has
  87 boxes.
- User approved the first executable recipe on 2026-06-21:
  `yolov8s.pt + AdamW/cos_lr/light-mixup`.
- User updated the product priority on 2026-06-21: prioritize model quality
  over the existing four-class detector contract; if useful, narrow the task to
  insulator classes only and rebuild/repartition the dataset.
- User approved the sampling policy on 2026-06-21: after duplicate-aware split,
  apply only light resampling on the training split. Validation and test splits
  must remain real, non-duplicated, and unresampled.
- User confirmed on 2026-06-21 that `prepare_dataset.py` and
  `validate_dataset.py` should remain separate entry points for now.
- Repository evidence indicates the Aerial source and DatasetNinja source have
  1,440 overlapping image filenames, matching the Aerial image count. Treat
  them as likely duplicate/repackaged insulator data until hash-level duplicate
  checks prove otherwise.

## Requirements

- Keep the first optimization training run bounded to 30 epochs unless the user
  explicitly changes the cap.
- Research optimization options before changing code or launching a new full
  run.
- Use a versioned candidate output directory for the next run instead of
  overwriting the previous baseline handoff.
- Prioritize model quality, especially damage recall, over strict comparability
  with the previous four-class baseline.
- Allow a reviewed detector contract change from four classes to an
  insulator-focused two-class candidate:
  - `insulator_normal`
  - `insulator_surface_damage`
- Allow train/val/test repartition for the insulator-focused candidate, but
  perform duplicate detection first and prevent the same source image from
  leaking across splits.
- Apply any class balancing only to train:
  - cap or downsample normal-heavy training images
  - lightly repeat or oversample damage-heavy training images
  - do not copy, oversample, or filter val/test to make metrics look better
- Prefer a new versioned dataset/model identity for contract-changing work, for
  example `edgeeye-insulator-v1`, instead of silently replacing
  `edgeeye-detector-v1`.
- Include dataset-folder cleanup and organization in the execution plan, while
  preserving ignored raw/model artifacts and avoiding destructive cleanup of
  user data.
- Keep generated weights, ONNX files, expected outputs, training runs, raw
  images, and processed images out of git.

## Acceptance Criteria

- [ ] A research note exists under this task describing practical optimization
      options, expected impact, cost, risks, and recommended first-pass recipe.
- [ ] `prd.md` records the chosen optimization scope and measurable success
      criteria for the insulator-focused candidate.
- [ ] For this complex task, `design.md` and `implement.md` exist before
      `task.py start`.
- [ ] The implementation plan uses a 30-epoch training cap for the next run.
- [ ] The plan includes dataset-folder organization/cleanup steps and clear
      non-destructive guardrails.
- [ ] The validation plan includes dataset validation, training metrics review,
      ONNX export, expected-output regeneration, ignored-artifact checks, and a
      comparison against the relevant baseline metrics.
- [ ] The insulator-focused dataset builder performs duplicate-aware splitting
      before training.
- [ ] The generated manifest/report records:
      - duplicate groups and any removed/merged duplicates
      - train-only normal cap/downsampling policy
      - train-only damage oversampling/repetition policy
      - unresampled val/test image and box counts
- [ ] Candidate success criteria prioritize insulator quality:
      - `insulator_surface_damage` recall improves materially over the previous
        four-class baseline value `0.46319`
      - `insulator_surface_damage` mAP50-95 improves materially over `0.27248`
      - normal-insulator precision does not collapse into excessive false
        damage positives
      - the report clearly states that metrics are not directly equivalent to
        the old four-class detector if the dataset/classes/splits change

## Out of Scope

- Atlas `.om` conversion unless the local CANN/Ascend `atc` environment is
  available.
- Production deployment of the optimized model.
- Backend/frontend inference API changes beyond documenting the new model
  contract.
- Moving top-level dataset archives into a new folder unless the preparation
  code is first updated to support both old and new archive lookup paths.
- Custom class-weighted loss or custom trainer checkpoint fitness in the first
  insulator-focused implementation.
- Merging `training/prepare_dataset.py` and `training/validate_dataset.py`.
  Keep generation and validation as separate commands for this task.

## Open Questions

- None blocking planning. Default to creating `edgeeye-insulator-v1` as a
  separate candidate while leaving `edgeeye-detector-v1` as the four-class
  baseline. Replace or promote only after explicit handoff review.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
