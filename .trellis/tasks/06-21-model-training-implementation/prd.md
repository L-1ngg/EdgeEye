# 模型训练实现

## Goal

在现有 `edgeeye-detector-v1` 本地数据集和 `training/` 训练环境基础上，跑通第一版 YOLO 检测模型的开发机侧训练、验证、ONNX 导出和交付包整理，让成员1可以继续做 Atlas `atc -> .om` 转换验证。

## Current Status

- 当前 Trellis task：`.trellis/tasks/06-21-model-training-implementation/`。
- 当前 task 状态：`planning`，尚未执行 `task.py start`。
- 上游调研 task `.trellis/tasks/archive/2026-06/06-18-model-training-research/` 已完成训练环境和数据集准备。
- 训练环境在 `training/`，使用 Python + `uv` + Ultralytics YOLO + PyTorch。
- 训练脚本已存在：`training/train.py`。
- ONNX 导出脚本已存在：`training/export_onnx.py`。
- 环境检查脚本已存在：`training/check_env.py`。
- 数据集校验脚本已存在：`training/validate_dataset.py`。
- 已生成本地 processed 数据集：`dataset/processed/edgeeye-detector-v1/`。
- 最新数据集规模记录在 `dataset/docs/edgeeye-detector-v1-report.md`：
  - total images: 10,411
  - total boxes: 145,382
  - `insulator_normal`: 135,814 boxes
  - `insulator_surface_damage`: 6,727 boxes
  - `transformer_normal`: 2,754 boxes
  - `transformer_surface_damage`: 87 boxes
- `models/` 当前不存在，说明还没有稳定输出的 `best.pt` / `best.onnx`。
- `models/`、`training/runs/`、`dataset/processed/` 均被 `.gitignore` 忽略，模型权重和训练产物不得提交到 git。

## Confirmed Detector Contract

第一版 detector-v1 固定四个类别，顺序必须保持一致：

| ID | Class | Contract mapping |
| ---: | --- | --- |
| 0 | `insulator_normal` | `deviceType: "insulator"`, `faultType: null` |
| 1 | `insulator_surface_damage` | `deviceType: "insulator"`, `faultType: "surface_damage"` |
| 2 | `transformer_normal` | `deviceType: "transformer"`, `faultType: null` |
| 3 | `transformer_surface_damage` | `deviceType: "transformer"`, `faultType: "surface_damage"` |

The same order must remain aligned across:

- `dataset/processed/edgeeye-detector-v1/dataset.yaml`
- `dataset/processed/edgeeye-detector-v1/classes.json`
- `dataset/processed/edgeeye-detector-v1/label.names`
- `training/config/classes.json`
- `training/config/label.names`
- generated YOLO labels

## Requirements

- Verify the local training environment before running training.
- Verify the processed dataset and class mapping before training.
- Run a short training smoke test first to prove that the training entry point, CUDA/device selection, dataset path, checkpoint copy, and ONNX export path work.
- Run the first baseline detector-v1 training pass using the current four-class dataset before this task is considered complete.
- Export the trained checkpoint to ONNX with `opset=11` and `imgsz=640`.
- Produce a local handoff package under ignored artifact paths, centered on `models/edgeeye-detector-v1/`.
- Produce a lightweight tracked model evaluation / handoff report that records:
  - training command and key parameters
  - environment evidence
  - dataset version and class distribution
  - validation metrics available from Ultralytics
  - known weak classes and likely failure cases
  - recommended `confidenceThreshold` and `nmsThreshold`
  - exact handoff files for Atlas conversion
- Produce an `expected-output-v1.json` handoff file with at least 5 validation/test images and expected detection outputs for development-machine comparison.
- Keep model weights, ONNX files, training runs, raw images, processed images, and other large artifacts ignored by git.
- Do not change backend/frontend API contracts or add detector classes in this task.

## Handoff Files

Local ignored artifacts expected after implementation:

- `models/edgeeye-detector-v1/best.pt`
- `models/edgeeye-detector-v1/best.onnx`
- `models/edgeeye-detector-v1/classes.json`
- `models/edgeeye-detector-v1/label.names`
- `models/edgeeye-detector-v1/preprocess-v1.json`
- `models/edgeeye-detector-v1/expected-output-v1.json`

Tracked documentation expected after implementation:

- A concise report under `docs/` or `dataset/docs/` documenting the first baseline model result and handoff package.

## Acceptance Criteria

- [ ] `cd training && uv run python check_env.py` passes or any environment limitation is explicitly recorded.
- [ ] `cd training && uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml --classes ../dataset/processed/edgeeye-detector-v1/classes.json --labels ../dataset/processed/edgeeye-detector-v1/label.names` passes before training.
- [ ] A short training smoke test completes and writes a stable checkpoint to `models/edgeeye-detector-v1/best.pt`.
- [ ] The smoke checkpoint can be exported to `models/edgeeye-detector-v1/best.onnx`, proving the training-to-export chain works before the full run.
- [ ] A baseline detector-v1 training run completes and metrics are recorded before the task is archived as complete.
- [ ] `training/export_onnx.py` exports `models/edgeeye-detector-v1/best.onnx` from the produced checkpoint.
- [ ] The handoff package contains `best.pt`, `best.onnx`, `classes.json`, `label.names`, `preprocess-v1.json`, and `expected-output-v1.json`.
- [ ] `expected-output-v1.json` contains at least 5 validation/test image cases with class IDs/names, confidence values or ranges, bounding boxes, image dimensions, and contract mapping.
- [ ] A tracked report records the training/export commands, environment, metrics, thresholds, known class imbalance risk, and Atlas handoff instructions.
- [ ] Git status does not include large dataset files, model weights, ONNX files, OM files, or `training/runs/`.

## Out Of Scope

- Atlas-side `atc` conversion and `.om` runtime validation.
- Backend API, database, frontend, or dashboard changes.
- New detector classes or enum changes.
- Fire/smoke environment-anomaly model training.
- New data collection, manual annotation, relabeling, balancing, or model tuning beyond the first baseline pass.
- Committing model binaries or processed image data to git.

## Risks

- `transformer_surface_damage` has only 87 boxes total and may be unreliable in the first baseline model.
- `insulator_normal` dominates the dataset after adding substation normal-device samples; fault recall may drop.
- A full training run may take a long time or fail if CUDA/PyTorch is unavailable in the current environment.
- `expected-output-v1.json` will reflect the first baseline model, not a final production threshold.

## Training Acceptance Policy

User-confirmed on 2026-06-21:

- The final goal for this task requires a complete baseline training run and recorded metrics.
- Before committing to the long run, first verify the chain with:
  - `check_env.py`
  - processed dataset validation
  - 1 epoch smoke training
  - ONNX export from the smoke checkpoint
- A successful smoke chain proves readiness but is not enough to complete or archive the task.
