# 模型训练需求调研与准备

## Goal

围绕成员2的视觉目标检测工作，整理训练前必须确认和准备的内容，让后续训练任务可以直接进入数据、标注、训练、导出和交付。

本 Task 只做规划和准备，不执行真实数据采集、标注、训练、调参、模型导出或 Atlas 部署。

## Current Status

- 当前任务状态：`in_progress`。
- 远端文档已更新，`docs/01-edge-atlas.md` 现在包含当前开发板、CANN 和摄像头实测基线。
- 已参考 `atlas-insulator-detection` 的现成链路，确认本项目训练主线采用 `dataset.yaml + label.names -> train.py -> best.pt -> best.onnx -> atc -> detector-v1.om`。
- 已新增独立 `training/` 训练环境，使用 `uv` 管理 PyTorch、Ultralytics、ONNX、ONNX Runtime、OpenCV、PyYAML 等训练依赖，避免污染后端 FastAPI 运行环境。
- 已新增 `training/config/classes.json`、`training/config/label.names`、`training/config/preprocess-v1.json` 和 `training/config/dataset.template.yaml`，固定第一版 4 类 detector-v1 类别顺序和预处理参数。
- 已新增 `training/prepare_dataset.py`、`training/validate_dataset.py`、`training/train.py`、`training/export_onnx.py` 和 `training/check_env.py`，覆盖数据转换、数据校验、训练、ONNX 导出和环境检查入口。
- 本机训练环境已验证：`torch==2.12.1+cu130`、`ultralytics==8.4.70`、ONNX Runtime 可导入，CUDA 可见 `NVIDIA GeForce RTX 4060 Laptop GPU`。
- 已全量生成 `dataset/processed/edgeeye-detector-v1/`，并通过 `dataset.yaml`、`label.names`、`classes.json` 一致性和 YOLO 标签范围校验。
- 已将 3 个本地归档解压并放置到 `dataset/raw/`：`insulator-defect-detection/`、`transformer-station-detection/`、`substation-equipment-15class/`；其中 `substation-equipment-15class/` 内部 4 个嵌套 zip 也已展开。
- 已实现 `substation-equipment-15class` 正常设备样本合并：`Glass disc insulator`、`Porcelain pin insulator` -> `insulator_normal`，`Power transformer` -> `transformer_normal`。
- 最新 processed 数据集包含 10,411 images、10,411 labels、145,382 boxes；其中 `substation:train` 5,668 images、`substation:val` 709 images、`substation:test` 709 images。
- 仍未执行正式训练、调参、`best.pt` 产出、`best.onnx` 导出或 Atlas `.om` 转换；这些进入后续训练实现任务。

## Confirmed Facts

### Member 2 Scope

- 成员2负责设备识别、外观故障检测、环境异常检测、数据准备、模型训练、模型导出和评估。
- 成员2不负责仪表读数识别、仪表数值超限判断、告警规则、后端数据库接口或前端页面。
- 第一版推荐走轻量 YOLO 路线，例如 `yolov8n.pt` 或 `yolov5n.yaml`。
- 第一版推荐模型输入尺寸为 `640x640`，batch 为 `1`。

### Atlas And Camera Constraints

来自 `docs/01-edge-atlas.md` 的当前实测基线：

- Atlas 商业型号：`Atlas 200I A2`。
- NPU / Chip：`310B4`。
- `soc_version`：`Ascend310B4`。
- CANN / Ascend toolkit：`7.0.RC1`，版本文件显示 `7.0.0.5.242`。
- `atc` 路径：`/usr/local/Ascend/ascend-toolkit/7.0.RC1/aarch64-linux/bin/atc`。
- `ACL_DEVICE_ID`：`0`。
- 摄像头：`Alcor Micro Corp. PC Camera`，USB ID `058f:1412`，USB UVC 摄像头。
- 采集节点：`/dev/video0`；元数据节点：`/dev/video1`。
- 支持格式：`MJPG`、`YUYV`。
- 当前测试配置：MJPG `640x480 @ 30 FPS`。
- 支持分辨率示例：`640x480`、`800x600`、`1280x720`、`1280x960`。
- 当前测试截图几乎全黑，说明采集链路可用，但演示前需要重新对准亮处或调整曝光。

### Contract Constraints

- 对外 JSON 字段和枚举必须遵守 `docs/contracts.md`、`docs/openapi.yaml` 和 `docs/api-spec.md`。
- `deviceType` 可用值包括：`meter`、`insulator`、`transformer`、`switchgear`、`circuit_breaker`、`unknown`。
- `faultType` 可用值包括：`surface_damage`、`rust`、`foreign_object`、`smoke`、`fire`、`person_intrusion`、`helmet_missing`、`unknown`。
- `classes.json` 的 `type` 必须使用 `modelClassType` 枚举，并且 `name` 必须能映射到 `deviceType` 或 `faultType`。
- 第一版不要为了训练临时新增接口枚举；如确需新增，必须先同步契约文档。

### Recommended Training And Delivery Flow

项目文档推荐主线：

```text
dataset.yaml + label.names
  -> train.py 训练得到 best.pt
  -> Ultralytics export 得到 best.onnx
  -> 昇腾环境使用 atc 转成 detector-v1.om
  -> Atlas 开发板通过 ACL 加载 OM 推理
```

第一版训练/导出配置建议：

- 输入尺寸：`640x640`。
- batch：`1`。
- ONNX 导出 `opset`：`11`。
- 置信度阈值初始值：`0.25` 或按评估报告收敛。
- NMS IoU 阈值初始值：`0.45`。
- 预处理必须和板端保持一致：BGR 转 RGB、resize、归一化到 `[0, 1]`、HWC 转 CHW、增加 batch 维度，最终输入 `NCHW`。
- 后处理必须包含置信度过滤、坐标映射回原图、NMS，并输出 `class_id`、`class_name`、`confidence`、`bbox`、`inference_ms` 和 `fps`。

## Recommended MVP Scope

第一版只保留公开数据能同时支撑“正常识别 + 故障识别”的设备类型。目标是在不新增契约枚举的前提下，让演示能覆盖可靠的“设备识别 + 外观故障识别”，不为了凑设备数量保留没有故障数据支撑的类别。

公开数据可得性结论：

- `insulator_normal` / `insulator_surface_damage` 支撑最强，可直接使用 Insulator-Defect Detection 和 Aerial Power Infrastructure Detection。
- `transformer_normal` / `transformer_surface_damage` 有可用公开数据，但样本量小于绝缘子，适合作为第二主线。
- `substation-equipment-15class` 已解压，可作为正常设备识别补充；只纳入 `Glass disc insulator`、`Porcelain pin insulator` 和 `Power transformer`，不直接纳入其余 12 类。
- `switchgear_normal` 有 electrical cabinet 数据支撑，但缺少直接可用的开关柜故障数据；第一版不做开关柜，避免只有正常设备识别、没有故障检测。
- `transformer_rust` 缺少高质量专用公开数据；第一版改用更泛化的 `surface_damage`，避免训练目标过窄。

推荐类别集合：

| 训练类别 | 契约映射 | 说明 |
| --- | --- | --- |
| `insulator_normal` | `deviceType: "insulator"`，`faultType: null` | 正常绝缘子，保证基础设备识别 |
| `insulator_surface_damage` | `deviceType: "insulator"`，`faultType: "surface_damage"` | 绝缘子表面破损，贴合参考项目和演示主线 |
| `transformer_normal` | `deviceType: "transformer"`，`faultType: null` | 正常变压器，扩展第二种设备 |
| `transformer_surface_damage` | `deviceType: "transformer"`，`faultType: "surface_damage"` | 变压器外观损坏，公开 transformer damage 数据比 rust 更可得 |

`substation-equipment-15class` 合入当前训练集时采用以下固定映射：

| Source class ID | Source class | Target class |
| ---: | --- | --- |
| 6 | `Glass disc insulator` | `insulator_normal` |
| 7 | `Porcelain pin insulator` | `insulator_normal` |
| 11 | `Power transformer` | `transformer_normal` |

暂不纳入：

- `Current transformer`、`Potential transformer`：名称含 transformer，但视觉形态和演示主线中的电力变压器不完全一致，先排除以降低类别语义漂移。
- 其余开关、断路器、避雷器、熔断器、重合器等 12 类：不属于当前 4 类 detector-v1 契约，保留给后续设备扩展任务。
- `substation-equipment-15class` 不提供故障语义，因此不映射到 `insulator_surface_damage` 或 `transformer_surface_damage`。

可选但不建议第一版强依赖：

- `switchgear_normal`：可作为后续设备识别扩展；但第一版不单独保留，因为缺少对应故障检测。
- `switchgear_surface_damage`：可作为开关柜对应故障的补标目标；公开数据不足，需要自采、合成或人工补标后再纳入主训练。
- `fire`：作为第二阶段环境异常检测目标，不和第一版设备故障模型一起强行训练。
- `smoke`：如后续环境异常素材不足，可作为备用环境异常类别。
- `meter`：当前不做读数识别；如加入，只作为普通设备类别，不做 OCR 和阈值判断。
- `circuit_breaker`：可作为后续第四种设备扩展。

## Requirements

- 梳理并固定第一版训练类别、类别顺序和契约映射。
- 整理训练前输入条件：数据来源、样本规模、标注规则、图片质量要求、版本命名。
- 明确训练最小闭环：数据集准备、训练、验证、导出、评估、交付成员1。
- 明确成员2交付给成员1的文件格式和一致性检查。
- 明确 Atlas 转换验证需要的测试样例和期望输出。
- 记录仓库当前缺失的训练目录、模型资产和外部确认事项。

## Preparation Checklist For Next Task

后续进入训练实现前，至少需要准备：

- `dataset/`：原始图片、清洗后图片、训练/验证/测试划分。
- `labels/`：YOLO 标注文件和标注规范。
- `training/`：训练脚本、训练配置、导出脚本或命令记录。
- `models/`：`best.pt`、`best.onnx`、后续转换得到的 `detector-v1.om`。
- `reports/`：模型评估报告、误报漏报样例、部署验证记录。
- `dataset.yaml`：固定数据路径、类别数量和类别顺序。
- `classes.json`：包含版本、类别 ID、类别名、类型和契约映射。
- `label.names`：顺序必须和 `dataset.yaml` 的 `names` 一致。
- `preprocess-v1.json`：输入尺寸、颜色通道、归一化、阈值。
- `expected-output-v1.json`：至少 5 张测试图的期望类别、bbox、confidence 范围和映射结果。
- 数据准备脚本需要支持从 `dataset/raw/substation-equipment-15class/` 读取 YOLO 标注，只保留 source class ID `6`、`7`、`11`，并重写为 detector-v1 class ID `0`、`2`。

## Acceptance Criteria

- [x] `prd.md` 清楚写出任务目标、已确认事实、调研范围和不做事项。
- [x] 文档中纳入最新 Atlas 开发板、CANN 和 USB 摄像头实测基线。
- [x] 文档中列出成员2训练所需的核心交付物和准备清单。
- [x] 文档中记录仓库当前缺失的训练相关目录、模型资产和配置文件。
- [x] 文档中给出推荐 MVP 类别集合和契约映射。
- [x] 文档中列出仍需用户或协作者确认的关键问题。
- [x] 用户确认第一版类别集合按公开数据可得性和故障检测完整性收敛后，本任务即可作为后续训练实现任务输入。
- [x] 用户确认 `24060960` 正常设备合并设计和实施计划，可作为下一阶段实现输入。

## Out Of Scope

- 实际采集、清洗、标注数据。
- 实际训练、调参、评估、导出或部署模型。
- Atlas 板端推理实现。
- 后端接口、数据库、前端页面实现。
- 仪表读数识别、OCR、阈值判断。
- 新增接口枚举或修改后端契约。

## Open Questions

1. 数据主要来自公开数据集，还是允许混入少量现场采集/合成样本补齐测试集？
2. 标注和评估由谁负责？是否需要先准备统一标注规范模板？
3. 火焰检测第二阶段是否允许单独训练一个 fire-only 模型，再决定是否合并进主模型？
4. 后续训练实现是否要先补目录骨架和 README，还是等真实数据/模型资产到位后再建？

## Recommended Next Decision

建议第一版先采用 4 个主训练类别：

```text
insulator_normal
insulator_surface_damage
transformer_normal
transformer_surface_damage
```

理由：

- 和现有契约完全兼容；
- 不需要新增后端或前端枚举；
- 覆盖 2 种设备，且每种设备都有正常和故障类别；
- 优先选择公开数据能支撑的类别，降低训练目标虚高风险；
- 绝缘子主线仍贴合 `atlas-insulator-detection` 参考路线；
- 类别数量适合先跑通 `best.pt -> best.onnx -> detector-v1.om -> Atlas` 闭环。

如果后续需要恢复第三种设备，再补充：

```text
switchgear_normal
switchgear_surface_damage
```

但开关柜故障类需要额外自采、合成或人工补标，不建议在完全依赖公开数据集时作为第一版硬性验收项。`fire` 进入第二阶段环境异常检测。

## Fire Detection Plan

火焰检测不放进第一版主模型的原因：

- 第一版主目标是电力设备及其外观故障闭环，必须先稳定交付 `best.pt -> best.onnx -> detector-v1.om -> Atlas`。
- `fire` 是环境异常，不依附某一个设备框；如果和设备故障一起训练，会引入大量负样本、阈值和误报评估问题。
- 火焰容易和红色/橙色物体、警示牌、灯光、反光、夕阳、屏幕图片混淆，需要单独做负样本测试。

推荐阶段安排：

| 阶段 | 目标 | 类别 | 交付 |
| --- | --- | --- | --- |
| Phase 1 | 设备和外观故障闭环 | `insulator_normal`、`insulator_surface_damage`、`transformer_normal`、`transformer_surface_damage` | 第一版 YOLO 模型、ONNX、类别映射、评估报告 |
| Phase 2A | 独立火焰检测验证 | `fire`，可选 `smoke` / `other` 作为辅助评估类 | fire-only 或 fire/smoke 验证模型、误报样例、推荐阈值 |
| Phase 2B | 决定集成方式 | 合并进主 YOLO 或保持独立 fire 模型 | 最终模型策略和 Atlas 部署方案 |

建议先做 Phase 2A 的独立模型，不直接合并进第一版主模型：

```text
fire
```

可选评估辅助类：

```text
smoke
other
```

集成策略：

- 如果 fire-only 模型在 Atlas 上 FPS 足够，可保持双模型：设备故障模型 + 火焰异常模型，降低类别互相干扰。
- 如果双模型 FPS 不足，再把 `fire` 合并进主 YOLO，形成一个多类别模型。
- 不论采用哪种方式，对后端上传仍映射为 `faultType: "fire"`，不新增接口枚举。

火焰检测数据优先级：

| 数据集 | 用途 | 备注 |
| --- | --- | --- |
| D-Fire | 主训练数据 | YOLO 格式，包含 fire、smoke、none，适合第一轮 fire/smoke 检测 |
| DFS Fire/Smoke | 质量验证和负样本补充 | 包含 fire、smoke、other，适合评估红橙色相似物体误报 |
| BoWFire / 小型 Roboflow fire 数据 | 额外 smoke/fire 样例或 sanity check | 样本量较小，不作为主数据来源 |
| 本地 USB 摄像头负样本 | 必须补充 | 红色物体、灯光、反光、屏幕图片、空场景，防止演示误报 |

Phase 2A 验收建议：

- `fire` 测试集 recall 不低于 `0.85`。
- 本地负样本 fire false positive rate 不高于 `5%`。
- 至少包含 30 张本地 USB 摄像头负样本。
- 给出推荐 `confidenceThreshold`，默认不低于 `0.4`，避免演示时火焰误报。
- 输出可用于 Atlas 转换验证的 fire `expected-output-v1.json`。

## Public Dataset Candidates

优先使用这些公开数据集作为第一版数据来源：

| 数据集 | 用途 | 备注 |
| --- | --- | --- |
| A YOLO Annotated 15-class Ground Truth Dataset for Substation Equipment | `insulator_normal`、`transformer_normal`，开关柜/同类电气设备仅作后续扩展参考 | 变电站场景、YOLO 标注、适合做设备识别底座 |
| Insulator-Defect Detection | `insulator_normal`、`insulator_surface_damage` | 类别包含 insulator、broken、pollution-flashover |
| Aerial Power Infrastructure Detection Train Dataset | `insulator_normal`、`insulator_surface_damage` | 有直接 tar 下载，适合作为绝缘子缺陷补充 |
| Transformer Station Detection | `transformer_normal`、`transformer_surface_damage` | 类别包含 normal、damage、graffiti；第一版只取 normal 和 damage |
| electrical cabinet | 后续 `switchgear_normal` 扩展 | 只有正常/设备识别价值，第一版不作为主训练类别 |
| Defects in Power Distribution Components | 辅助绝缘子/线缆故障分析，不直接作为三设备主类别 | 包含 cable out of insulator、cable out of spacer、insulator without ring |
| D-Fire | 第二阶段 `fire` / `smoke` 环境异常检测 | 作为火焰检测主数据来源，不进入第一版设备故障主模型 |
| DFS Fire/Smoke | 第二阶段火焰检测质量验证 | 包含 `other`，适合评估红橙色相似物体误报 |

## Notes

- 这是轻量规划任务，当前保留 PRD 即可。
- 不创建 `design.md` 和 `implement.md`，除非后续要进入真实训练实现。
- 第一版已按公开数据可得性和故障检测完整性收敛为 2 个设备、4 个主训练类别；`switchgear_normal`、`switchgear_surface_damage` 暂作为后续设备扩展候选；`fire` 作为第二阶段环境异常检测单独规划。
