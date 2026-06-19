# 24060960 Normal Device Merge Implementation Plan

## Scope

Implement dataset preparation support for merging selected normal-device classes
from `dataset/raw/substation-equipment-15class/` into
`dataset/processed/edgeeye-detector-v1/`.

Do not train a model, export ONNX, run Atlas `atc`, or modify backend/frontend
code.

## Implementation Checklist

1. Update `training/prepare_dataset.py`.
   - Add a `SUBSTATION_LABEL_MAP` for source IDs `6`, `7`, and `11`.
   - Add helper logic to locate sibling images by stem and supported suffix.
   - Add a deterministic 80/10/10 split helper for sources without existing
     train/val/test directories.
   - Add `convert_substation_equipment(output, limit_per_source)`.
   - Merge its stats after the existing aerial, DatasetNinja, and transformer
     converters.
   - Extend `inventory()` with `substation-equipment-15class` raw directory
     counts.

2. Preserve detector-v1 contract.
   - Keep `CLASS_NAME_TO_ID` unchanged.
   - Keep `dataset.yaml` names unchanged.
   - Keep `training/config/classes.json` and `training/config/label.names`
     unchanged.

3. Regenerate the processed dataset.
   - First run a smoke conversion with `--limit-per-source`.
   - Then run a full conversion with `--overwrite`.

4. Update dataset reporting docs after full conversion.
   - `dataset/README.md`
   - `dataset/docs/edgeeye-detector-v1-report.md`
   - Add final split counts, source counts, class distribution, skipped images,
     skipped boxes, and excluded substation source classes.

5. Review generated `manifest.json`.
   - Confirm source keys include `substation:train`, `substation:val`, and
     `substation:test`.
   - Confirm `classMap` still has exactly four detector-v1 classes.
   - Confirm class boxes increased only for `insulator_normal` and
     `transformer_normal` from the substation source.

## Validation Commands

Run from repo root unless noted.

```bash
cd training
uv run python prepare_dataset.py --limit-per-source 20 --overwrite
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
uv run python prepare_dataset.py --overwrite
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
```

Optional environment check:

```bash
cd training
uv run python check_env.py
```

## Expected Evidence

Before implementation, candidate source evidence is:

| Metric | Value |
| --- | ---: |
| source label files | 7,537 |
| source files with kept boxes | 7,094 |
| kept labels missing sibling images | 8 |
| `Glass disc insulator` boxes | 14,269 |
| `Porcelain pin insulator` boxes | 118,381 |
| `Power transformer` boxes | 2,541 |

The final full conversion may produce fewer than 7,094 substation images because
the eight missing-image labels must be skipped.

## Risk And Rollback

- Risk: normal classes become much larger than fault classes.
  - Mitigation: record class distribution in the report; add balancing only in a
    later training task if metrics show fault recall loss.

- Risk: source file naming collisions.
  - Mitigation: prefix generated files with sanitized relative source path.

- Risk: malformed labels or missing sibling images.
  - Mitigation: skip and count them in `skippedBoxes`, `skippedImages`, and
    `excludedClasses`; do not fail the whole conversion unless no data is
    generated.

- Rollback point: rerun the previous converter behavior by removing
  `convert_substation_equipment` from the stats merge and regenerating
  `dataset/processed/edgeeye-detector-v1/`.

## Ready-To-Start Criteria

- `prd.md`, `design.md`, and `implement.md` are present.
- The workflow state has moved out of planning.
- User has explicitly approved the design and implementation plan.
- `task.py start` has been run for this Trellis task before code changes.
