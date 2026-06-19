# 24060960 Normal Device Merge Design

## Objective

Extend the detector-v1 dataset preparation plan so the extracted 15-class
substation equipment source can safely add normal-device examples to the current
4-class YOLO training dataset.

This design covers dataset conversion only. It does not cover model training,
ONNX export, Atlas `.om` conversion, backend API changes, or frontend changes.

## Current Dataset Contract

The detector-v1 class order remains fixed:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |
| 2 | `transformer_normal` |
| 3 | `transformer_surface_damage` |

`dataset.yaml`, `label.names`, `classes.json`, and generated YOLO label files
must all preserve this order.

## Source Evidence

The extracted substation dataset lives at:

```text
dataset/raw/substation-equipment-15class/
```

It contains:

- `classes.txt`
- nested source directories: `misc/`, `agv_day/`, `agv_night_dark/`,
  `agv_night_light/`
- 7,531 image files
- 7,537 YOLO label files
- source class IDs `0` through `14`

Confirmed source class mapping:

| Source ID | Source class | Target class |
| ---: | --- | --- |
| 6 | `Glass disc insulator` | `insulator_normal` |
| 7 | `Porcelain pin insulator` | `insulator_normal` |
| 11 | `Power transformer` | `transformer_normal` |

Measured candidate volume:

| Source class | Target class | Boxes |
| --- | --- | ---: |
| `Glass disc insulator` | `insulator_normal` | 14,269 |
| `Porcelain pin insulator` | `insulator_normal` | 118,381 |
| `Power transformer` | `transformer_normal` | 2,541 |

7,094 source label files contain at least one kept box. Eight of those labels do
not have a matching sibling image file and should be skipped as missing images.

## Exclusions

Do not include:

- `Current transformer` and `Potential transformer`, because they are visually
  different from the main power-transformer demo class.
- All switch, breaker, fuse, arrester, recloser, muffle, and other source
  classes outside detector-v1.
- Any substation source boxes as `insulator_surface_damage` or
  `transformer_surface_damage`, because this dataset is equipment detection, not
  fault detection.

Excluded source class IDs should be counted in `excludedClasses` so future
reports can explain why boxes were dropped.

## Conversion Design

Add a new converter to `training/prepare_dataset.py`:

```text
convert_substation_equipment(output, limit_per_source) -> ConversionStats
```

The converter should:

1. Find `dataset/raw/substation-equipment-15class/`.
2. Walk all non-`classes.txt` YOLO label files under that root.
3. Treat each label file's grandparent directory as its image directory.
   For example:

```text
dataset/raw/substation-equipment-15class/agv_day/agv_day/labels/foo.txt
dataset/raw/substation-equipment-15class/agv_day/agv_day/foo.jpg
```

4. Find a sibling image with the same stem and a supported image suffix.
5. Read YOLO boxes and keep only source IDs `6`, `7`, and `11`.
6. Rewrite kept source IDs to detector-v1 target classes:
   - `6`, `7` -> `insulator_normal`
   - `11` -> `transformer_normal`
7. Copy one source image only when at least one kept box remains.
8. Write the rewritten label file under the generated split.
9. Count missing sibling images as skipped images.
10. Count malformed or invalid boxes as skipped boxes.
11. Count all non-kept valid boxes in `excludedClasses`.

## Split Strategy

The source does not expose train/val/test directories. Use a deterministic split
based on sorted label paths:

| Split | Ratio |
| --- | ---: |
| train | 80% |
| val | 10% |
| test | 10% |

The split must be deterministic across runs. A stable approach is:

- collect all label files with at least one kept box and matching image
- sort by relative path
- assign by index ratio

For `--limit-per-source`, apply the limit after sorting the eligible file list.
This keeps smoke conversions predictable.

## Naming

Generated image and label names should include a source prefix and a sanitized
relative stem to avoid collisions between nested source folders.

Example:

```text
substation_agv_day_agv_day_FLIR7531_rgb.jpg
substation_agv_day_agv_day_FLIR7531_rgb.txt
```

## Manifest Changes

`manifest.json` should continue using the existing schema, with additional
source keys such as:

```text
substation:train
substation:val
substation:test
```

Expected manifest effects after a full rebuild:

- total images and labels increase
- `insulator_normal` and `transformer_normal` boxes increase significantly
- `insulator_surface_damage` and `transformer_surface_damage` stay unchanged
  except for any existing source behavior
- `excludedClasses` includes dropped substation source IDs

## Validation

Required validation after implementation:

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

## Risks

- The substation source adds many more normal boxes than fault boxes. Training
  may need later balancing or sampling if fault recall drops.
- `Porcelain pin insulator` dominates the added normal-insulator boxes.
- Eight candidate source labels currently lack sibling images. These should be
  skipped and reported, not treated as fatal.
- The added source is normal-device data only. Evaluation reports must avoid
  claiming it improves fault examples.
