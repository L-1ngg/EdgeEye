# Dataset Sources

## Phase 1 Device And Fault Detection

### Substation Equipment 15-class YOLO Dataset

- Purpose: `insulator_normal`, `transformer_normal`, and electrical equipment reference images.
- Source page: <https://figshare.com/articles/dataset/A_YOLO_Annotated_15-class_Ground_Truth_Dataset_for_Substation_Equipment/24060960>
- Local target: `dataset/raw/substation-equipment-15class/`
- Status: downloaded, extracted, and placed.
- Local archive: `dataset/downloads/24060960.zip`.
- Local extracted path: `dataset/raw/substation-equipment-15class/`.
- Attempted on 2026-06-18: Figshare API and `ndownloader` endpoints returned HTTP 403 from this runtime.
- Verified on 2026-06-19:
  - Outer archive entries: `misc.zip`, `agv_night_light.zip`, `agv_night_dark.zip`, `agv_day.zip`, `classes.txt`.
  - Nested archives extracted under `misc/`, `agv_night_light/`, `agv_night_dark/`, and `agv_day/`.
  - Extracted inventory: 7,531 images, 7,537 YOLO label files, 15 source classes.
  - Source label files contain YOLO normalized boxes with class IDs `0` through `14`.
- Confirmed detector-v1 mapping:
  - `6` / `Glass disc insulator` -> `insulator_normal`.
  - `7` / `Porcelain pin insulator` -> `insulator_normal`.
  - `11` / `Power transformer` -> `transformer_normal`.
- Excluded from detector-v1:
  - `12` / `Current transformer` and `13` / `Potential transformer`, because their visual semantics differ from the main power-transformer demo class.
  - All other source classes, because they are outside the current 4-class detector contract.
- Current use: included in `edgeeye-detector-v1`; the preparation script keeps only the confirmed source class IDs and rewrites them to detector-v1 class IDs.

### Insulator-Defect Detection

- Purpose: `insulator_normal`, `insulator_surface_damage`.
- Dataset Ninja page: <https://datasetninja.com/insulator-defect-detection>
- Roboflow page: <https://universe.roboflow.com/insulator-defect-detection/insulator-defect-detection-veowd>
- Local target: `dataset/raw/insulator-defect-detection/`
- Status: downloaded, extracted, and placed from the DatasetNinja archive.
- Local archive: `dataset/downloads/insulator-defect-detection-DatasetNinja.tar`.
- Local extracted path: `dataset/raw/insulator-defect-detection/`.
- Attempted on 2026-06-18: Roboflow YOLO download endpoint returned HTTP 403 with a Cloudflare challenge.
- Verified on 2026-06-19:
  - Train split: 1,296 images, 1,296 annotation files.
  - Validation split: 144 images, 144 annotation files.
  - Test split: 160 images, 160 annotation files.
  - Metadata file: `meta.json`.
- Next action: keep using the extracted DatasetNinja archive for the first insulator slice; use Roboflow only if a separate authenticated export is needed.

### Aerial Power Infrastructure Detection Train Dataset

- Purpose: `insulator_normal`, `insulator_surface_damage`.
- Source page: <https://github.com/supervisely-ecosystem/aerial-power-infrastructure-detection-train-dataset>
- Local target: `dataset/raw/aerial-power-infrastructure-detection-train/`
- Status: downloaded and placed.
- Local path: `dataset/raw/aerial-power-infrastructure-detection-train/`
- Download method: `git clone --depth 1`.
- Verified on 2026-06-18:
  - Size: about 266 MB.
  - Train split: 1,296 images, 1,296 annotation files.
  - Validation split: 144 images, 144 annotation files.
  - Source labels: `insulator`, `broken`, `pollution-flashover`.
  - Object counts: `pollution-flashover` 2,223; `insulator` 1,645; `broken` 963.
- Notes: annotations are Supervisely JSON and must be converted/remapped before YOLO training.

### Transformer Station Detection

- Purpose: `transformer_normal`, `transformer_surface_damage`.
- Source page: <https://universe.roboflow.com/mehran-uet-jamshtoro/transformer-station-detection>
- Local target: `dataset/raw/transformer-station-detection/`
- Status: downloaded, extracted, and placed.
- Local archive: `dataset/downloads/Transformer Station Detection.v1i.yolov8.zip`.
- Local extracted path: `dataset/raw/transformer-station-detection/`.
- Attempted on 2026-06-18: Roboflow YOLO download endpoint returned HTTP 403 with a Cloudflare challenge.
- Verified on 2026-06-19:
  - Train split: 353 images, 353 label files.
  - Validation split: 57 images, 57 label files.
  - Test split: 29 images, 29 label files.
  - Dataset file: `data.yaml`.
- Next action: keep using the extracted archive; use Roboflow only if a refreshed authenticated export is needed.

## Phase 2 Fire Detection

### D-Fire

- Purpose: `fire`, optional `smoke`, fire negative examples.
- Source page: <https://github.com/gaia-solutions-on-demand/DFireDataset>
- Local target: `dataset/raw/d-fire/`
- Status: not downloaded.
- Attempted on 2026-06-18: GitHub repository contains documentation and utilities, not the full image dataset. The dataset links are hosted through OneDrive/Kaggle-style distribution, and Kaggle CLI is not installed/authenticated in this runtime.
- Next action: download manually from the provider links or provide Kaggle credentials/direct archive URL.

### DFS Fire Smoke Dataset

- Purpose: fire quality validation and negative samples.
- Source page: <https://github.com/siyuanwu/DFS-FIRE-SMOKE-Dataset>
- Local target: `dataset/raw/dfs-fire-smoke/`
- Status: not downloaded.
- Attempted on 2026-06-18: GitHub repository contains documentation, while full data is linked through BaiduYun/OneDrive-style external storage.
- Next action: download manually from the provider links or provide a direct archive URL.
