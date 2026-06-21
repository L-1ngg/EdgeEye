# Dataset Preparation Contract

## Scenario: Detector-v1 Source Conversion And Insulator-v1 Candidate Conversion

### 1. Scope / Trigger

This spec applies when changing:

- `training/prepare_dataset.py`
- detector-v1 class mappings
- insulator-v1 candidate class mappings
- raw source inclusion or exclusion rules
- generated dataset metadata and reports

The default detector-v1 conversion output is:

```text
dataset/processed/edgeeye-detector-v1/
```

The insulator-focused optimization candidate output is:

```text
dataset/processed/edgeeye-insulator-v1/
```

Recall-focused successors must use distinct versioned output paths, for
example:

```text
dataset/processed/edgeeye-insulator-v1-domain-r1/
```

Do not treat this output as source-controlled application code. It is generated
training data and must remain ignored by git.

### 2. Signatures

Primary command:

```bash
cd training
uv run python prepare_dataset.py --overwrite
```

Smoke command:

```bash
cd training
uv run python prepare_dataset.py --limit-per-source 20 --overwrite
```

Validation command:

```bash
cd training
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json \
  --labels ../dataset/processed/edgeeye-detector-v1/label.names
```

Insulator-v1 candidate command:

```bash
cd training
uv run python prepare_dataset.py --variant edgeeye-insulator-v1 --overwrite
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1/label.names
```

Source-style controlled insulator candidate command:

```bash
cd training
uv run python prepare_dataset.py \
  --variant edgeeye-insulator-v1 \
  --output ../dataset/processed/edgeeye-insulator-v1-domain-r1 \
  --insulator-source-policy domain-r1 \
  --insulator-normal-cap-ratio 2 \
  --insulator-damage-repeat 2 \
  --overwrite
uv run python validate_dataset.py \
  --dataset ../dataset/processed/edgeeye-insulator-v1-domain-r1/dataset.yaml \
  --classes ../dataset/processed/edgeeye-insulator-v1-domain-r1/classes.json \
  --labels ../dataset/processed/edgeeye-insulator-v1-domain-r1/label.names
```

Converter signature pattern:

```python
def convert_<source>(output: Path, limit_per_source: int | None) -> ConversionStats:
    ...
```

### 3. Contracts

Detector-v1 class order is fixed:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |
| 2 | `transformer_normal` |
| 3 | `transformer_surface_damage` |

The same order must appear in:

- `training/config/classes.json`
- `training/config/label.names`
- generated `dataset.yaml`
- generated YOLO label class IDs

Insulator-v1 candidate class order is fixed:

| ID | Class |
| ---: | --- |
| 0 | `insulator_normal` |
| 1 | `insulator_surface_damage` |

Insulator-v1 candidate conversion rules:

- Keep it as a separate variant; do not silently overwrite
  `edgeeye-detector-v1`.
- Include Aerial and DatasetNinja Supervisely insulator data.
- Include substation `6` / `Glass disc insulator` and `7` /
  `Porcelain pin insulator` only as `insulator_normal`.
- Exclude transformer source data and all non-insulator substation classes.
- Build duplicate groups before train/val/test assignment using image SHA-256
  and Supervisely filename keys.
- Keep all duplicate group members in one split by selecting one canonical
  sample before splitting. Prefer damage-positive samples, then samples with
  more boxes, then Aerial over DatasetNinja over substation when choosing the
  canonical sample.
- Split unique samples by image-level damage presence into deterministic
  80/10/10 train/val/test partitions.
- Apply normal-only downsampling and damage-positive repetition only to train.
- Expose insulator train-only sampling as explicit CLI knobs:
  `--insulator-normal-cap-ratio`, `--insulator-damage-repeat`, and
  `--insulator-source-policy`.
- `--insulator-source-policy all` preserves the legacy source behavior.
- `--insulator-source-policy domain-r1` is not aerial-only; it keeps
  damage-positive samples, prefers non-substation normal-only samples, and
  keeps capped substation normal-only samples as hard negatives.
- Keep validation and test real, duplicate-safe, and unresampled.
- Record duplicate counts, raw duplicate-safe split counts, source audits, and
  train sampling policy in `manifest.json` and the tracked dataset report.

Source mappings:

| Source | Source label / ID | Target |
| --- | --- | --- |
| Aerial Power Infrastructure | `insulator` | `insulator_normal` |
| Aerial Power Infrastructure | `broken` | `insulator_surface_damage` |
| Aerial Power Infrastructure | `pollution-flashover` | `insulator_surface_damage` |
| Insulator-Defect DatasetNinja | `insulator` | `insulator_normal` |
| Insulator-Defect DatasetNinja | `broken` | `insulator_surface_damage` |
| Insulator-Defect DatasetNinja | `pollution-flashover` | `insulator_surface_damage` |
| Transformer Station Detection | `normal` / `2` | `transformer_normal` |
| Transformer Station Detection | `damage` / `0` | `transformer_surface_damage` |
| Transformer Station Detection | `graffiti` / `1` | excluded |
| Substation Equipment 15-class | `6` / `Glass disc insulator` | `insulator_normal` |
| Substation Equipment 15-class | `7` / `Porcelain pin insulator` | `insulator_normal` |
| Substation Equipment 15-class | `11` / `Power transformer` | `transformer_normal` |

Substation exclusions:

- `12` / `Current transformer` and `13` / `Potential transformer` remain
  excluded because their visual semantics differ from the power-transformer demo
  class.
- All other substation source classes are outside the current detector-v1
  contract.
- Substation source data is normal-device data only and must not be mapped to
  `insulator_surface_damage` or `transformer_surface_damage`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Output directory exists and `--overwrite` is not passed | Exit with a clear message |
| Source archive or directory is missing | Skip that source and continue |
| Source image is missing for a kept label | Increment `skippedImages`, skip that generated item |
| Source box has invalid class or malformed values | Increment `skippedBoxes` or `excludedClasses` |
| YOLO box values are not normalized or width/height are non-positive | Increment `skippedBoxes` |
| `--limit-per-source` is used for a smoke conversion | Limit generated samples only; keep scan-level skip and exclusion counters truthful for the scanned source |
| Final conversion has zero images or zero boxes | Exit non-zero |
| `dataset.yaml`, `classes.json`, and `label.names` disagree | `validate_dataset.py` must fail |
| Insulator-v1 val/test are resampled | Treat as invalid candidate data; regenerate with resampling limited to train |
| Duplicate sample keys cross train/val/test for insulator-v1 | Treat as invalid candidate data; fix grouping before training |

### 5. Good/Base/Bad Cases

Good:

- A substation label has source classes `6` and `7`; generated labels use class
  ID `0`.
- A substation label has source class `11`; generated labels use class ID `2`.
- `graffiti` boxes are counted in `excludedClasses` and never appear in
  generated labels.

Base:

- Running `prepare_dataset.py --overwrite` regenerates train/val/test directories
  and writes `manifest.json` with source counts, split counts, class counts,
  skipped counts, and excluded class counts.
- Running `prepare_dataset.py --limit-per-source 20 --overwrite` writes only a
  small deterministic sample, but still scans the substation labels so
  `skippedImages` and `excludedClasses` describe source quality rather than only
  the generated subset.
- Running `prepare_dataset.py --variant edgeeye-insulator-v1 --overwrite`
  creates a separate two-class dataset and leaves the four-class processed
  detector-v1 dataset untouched.

Bad:

- Mapping all 15 substation source classes directly into detector-v1 labels.
- Mapping `Current transformer` or `Potential transformer` to
  `transformer_normal` without a new reviewed decision.
- Mapping substation source data to any fault class.

### 6. Tests Required

Required checks after source mapping changes:

- `python -m py_compile training/prepare_dataset.py training/validate_dataset.py`
- smoke conversion with `--limit-per-source`
- full conversion with `--overwrite`
- full validation with explicit `--dataset`, `--classes`, and `--labels`
- for insulator-v1 changes, run the same smoke/full/validation sequence with
  `--variant edgeeye-insulator-v1`
- review generated `manifest.json` for:
  - exactly four target classes
  - source keys for all included sources
  - expected split counts
  - skipped images and excluded classes documented in the dataset report
- for insulator-v1, review `manifest.json` for exactly two target classes,
  duplicate summary, raw duplicate-safe split counts, source audit fields, and
  train-only sampling policy

### 7. Wrong vs Correct

#### Wrong

```python
SUBSTATION_LABEL_MAP = {
    6: "insulator_normal",
    7: "insulator_normal",
    11: "transformer_normal",
    12: "transformer_normal",
    13: "transformer_normal",
}
```

This silently broadens `transformer_normal` beyond the approved power-transformer
contract.

#### Correct

```python
SUBSTATION_LABEL_MAP = {
    6: "insulator_normal",
    7: "insulator_normal",
    11: "transformer_normal",
}
```

Keep `Current transformer` and `Potential transformer` excluded unless a future
task explicitly changes the detector contract and documents the evaluation
impact.
