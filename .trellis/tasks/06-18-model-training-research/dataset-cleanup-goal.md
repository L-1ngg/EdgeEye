整理 EdgeEye 当前本地数据集，使它可以可靠用于第一版 YOLO 训练。

  上下文：
  - 工作目录是 /home/l1ngg/dev/EdgeEye。
  - 先读取 AGENTS.md、dataset/README.md、dataset/docs/sources.md、training/README.md、training/prepare_dataset.py、
  training/validate_dataset.py、.trellis/tasks/06-18-model-training-research/prd.md。
  - 当前目标类别固定为：
    0 insulator_normal
    1 insulator_surface_damage
    2 transformer_normal
    3 transformer_surface_damage
  - 当前训练环境已经在 training/ 下搭好，使用 uv、Ultralytics YOLO、PyTorch、ONNX、ONNX Runtime。

  要做：
  1. 盘点 dataset/ 下所有原始数据、压缩包、已解压数据和 processed 数据，输出清晰 inventory。
  2. 不删除原始数据，不覆盖无法确认来源的数据；如需移动或重命名，先保留可追溯记录。
  3. 整理 dataset/raw、dataset/staging、dataset/processed 的结构，让来源、格式、用途清楚。
  4. 检查 Aerial Power Infrastructure、Insulator-Defect、Transformer Station 数据是否都能被训练脚本消费。
  5. 必要时改进 training/prepare_dataset.py，让它能处理当前实际文件位置，而不是依赖旧路径。
  6. 重新生成 dataset/processed/edgeeye-detector-v1/，并生成 dataset.yaml、classes.json、label.names、preprocess-v1.json、
  manifest.json。
  7. 校验类别顺序、标签范围、图片/label 对应关系、每个 split 的样本数和每类 bbox 数。
  8. 产出一个数据整理报告，说明每个数据源用了哪些类别、排除了哪些类别、跳过了多少样本、剩余风险是什么。
  9. 只整理数据和训练准备，不进行正式训练，不导出 best.pt / best.onnx，不做 Atlas atc 转换。

  完成标准：
  - `cd training && uv run python check_env.py` 通过。
  - `cd training && uv run python prepare_dataset.py --overwrite` 能完成全量转换。
  - `cd training && uv run python validate_dataset.py --dataset ../dataset/processed/edgeeye-detector-v1/dataset.yaml
  --classes ../dataset/processed/edgeeye-detector-v1/classes.json --labels ../dataset/processed/edgeeye-detector-v1/
  label.names` 通过。
  - `dataset/processed/edgeeye-detector-v1/manifest.json` 包含总图片数、label 数、bbox 数、每个 source 的样本数和
  classMap。
  - 报告中明确列出 train/val/test 的图片数、label 数、bbox 数，以及 4 个目标类别的样本分布。
  - git status 中不包含训练产物、图片、视频、模型权重或 .venv；这些大文件必须保持 ignored。