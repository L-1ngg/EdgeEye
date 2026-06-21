# 成员2：数据集与视觉目标检测

## 开发目标

负责所有基于摄像头画面的通用视觉检测任务，包括设备识别、设备外观故障检测和一种环境异常检测。

成员2解决的问题：

```text
画面中有什么、目标在哪里、是否出现肉眼可见的异常。
```

## 职责范围

主负责：

- 设备类别定义；
- 故障类别定义；
- 数据收集、清洗和标注；
- 目标检测模型训练；
- 外观故障检测；
- 环境异常检测；
- 模型导出和评估。

不负责：

- 仪表读数识别；
- 仪表数值是否超限；
- 仪表专项算法；
- 告警规则；
- 后端数据库和接口；
- 前端页面展示。

## 推荐检测类别

参考 [`atlas-insulator-detection`](https://gitee.com/jerry12345555555/atlas-insulator-detection)，两周内优先把绝缘子作为核心目标，先形成一条稳定的检测与部署链路。

设备类别建议从以下类别中选择 3 种左右：

```text
仪表
绝缘子
变压器
开关柜
断路器
```

故障类别建议从以下类别中选择 2 种左右：

```text
破损
锈蚀
异物
鸟巢
烟雾
明火
```

推荐第一版类别映射：

| 训练类别 | 契约映射 |
| --- | --- |
| `insulator_normal` | `deviceType: "insulator"`，`faultType: null` |
| `insulator_surface_damage` | `deviceType: "insulator"`，`faultType: "surface_damage"` |
| `foreign_object` | `faultType: "foreign_object"` |
| `bird_nest` | 优先映射为 `faultType: "foreign_object"`，前端展示为鸟巢/异物 |

环境异常建议只实现一种摄像头可见异常：

- 烟雾；
- 明火；
- 人员闯入；
- 安全帽检测。

两周内推荐选择 `烟雾` 或 `明火`，便于演示和数据准备。

## 输入

- 项目题目要求；
- 现场或网络收集的设备图片；
- 故障和环境异常图片；
- 成员1反馈的 Atlas 模型输入限制。

## 输出

模型输出示例：

```json
{
  "category": "insulator_surface_damage",
  "deviceType": "insulator",
  "faultType": "surface_damage",
  "confidence": 0.91,
  "bbox": [120, 80, 360, 420]
}
```

需要交给成员1：

- 模型文件；
- 类别文件；
- 输入尺寸；
- 预处理方式；
- 后处理方式；
- 置信度阈值建议；
- NMS 阈值建议；
- 类别到 `deviceType`、`faultType` 的映射表；
- `modelVersion`、`classesVersion` 和推荐阈值版本；
- 用于 Atlas 转换验证的 `expected-output-v1.json`。

## 当前模型交付状态

2026-06-21 当前仓库已有一版临时模型与接入配置：

| 文件 | 当前状态 |
| --- | --- |
| `models/artifacts/detector-transformer-v1.onnx` | 已放在本地 artifacts 目录，Git 忽略，不进入仓库 |
| `dataset/artifacts/transformer-roboflow-v2-yolov8.zip` | 已放在本地 dataset artifacts 目录，Git 忽略，不进入仓库 |
| `model-deploy/classes-v1.json` | 当前只映射 `class_id=0` 到 `transformer` |
| `model-deploy/label.names` | 当前只有一行 `transformer` |
| `model-deploy/preprocess-v1.json` | 当前记录 `640x640`、RGB、归一化、`conf=0.25`、`iou=0.45` |
| `model-deploy/expected-output-v1.json` | 当前 5 张本地测试图的 ONNX smoke 基准，用于后续 Atlas OM/ACL 输出对比 |
| `model-deploy/artifacts/transformer-v1-test-images/` | 当前 5 张本地测试图、标注图和 payload 输出，Git 忽略，不进入仓库 |

已确认的限制：

- 当前模型是 `detect` 检测模型，不是最终 Atlas OM 模型；
- 当前只有 `transformer` 一类，只能做变压器设备检测；
- 当前模型只训练 3 轮，本阶段只验联调链路，不验识别准确率；
- 当前输出 `faultType: null`，不能触发故障、告警或维修建议；
- 当前数据集里存在 bbox 与 polygon 标注混合的迹象，训练方需要确认导出/训练口径；
- 当前 ONNX 可用于开发机联调，但正式开发板仍需转换为 `.om` 并在 Atlas ACL 路线验证。

训练成员下一版至少需要补充：

- `best.onnx` 或更明确版本名的 ONNX 模型；
- `data.yaml` 或 `label.names`，保证类别顺序和 class id 明确；
- 模型类型：`detect` 或 `segment`；
- 输入尺寸、预处理方式和后处理阈值；
- 至少 5 张测试图片和每张图的期望检测结果；
- 如果要支持故障告警，类别必须能映射到 `faultType` 枚举。

## 任务清单

### 类别与标注规范

- 明确最终设备识别类别；
- 明确最终故障检测类别；
- 明确环境异常类别；
- 制定统一标注规范；
- 规定检测框标注边界；
- 规定遮挡、模糊、小目标和重复目标的处理方式；
- 固定类别命名，避免训练和部署时标签不一致。
- 类别命名必须和 [数据契约与接口规范](./contracts.md) 中的枚举保持一致，确需新增类别时先更新契约文档。
- 提供 `classes.json` 到 `deviceType`、`faultType` 的显式映射，不允许成员1靠字符串猜测。

### 数据集准备

- 收集正常设备图片；
- 收集故障设备图片；
- 如选择仪表作为普通设备类别，收集仪表外观图片；
- 收集环境异常图片；
- 清洗重复、过暗、过糊和明显无效图片；
- 按训练集、验证集、测试集拆分；
- 保存数据来源和样本数量统计。

### 模型训练

- 优先选择 Ultralytics YOLO 轻量模型，例如 `yolov8n.pt` 或 `yolov5n.yaml`；
- 使用 `dataset.yaml` 固定数据路径、类别数量和类别顺序；
- 配置类别数和输入尺寸；
- 推荐第一版输入尺寸为 `640`；
- 完成第一版训练；
- 根据误检和漏检结果补充数据；
- 完成第二版优化训练；
- 固定最终模型和参数。

### 模型导出

- 保存训练得到的 `best.pt`；
- 导出 ONNX 模型；
- 检查 ONNX 输入输出节点；
- 提供 `classes.json`；
- 提供 `label.names`，顺序必须和训练 `dataset.yaml` 的 `names` 一致；
- 提供预处理说明；
- 提供后处理说明；
- 与成员1一起验证 Atlas 转换结果。
- 交付 `preprocess-v1.json` 或等价说明，字段参考 [工程规范与联调标准](./engineering-standards.md)。
- 交付 `expected-output-v1.json`，用于比较开发机 ONNX 推理和 Atlas 推理结果。

### 评估分析

- 统计每类准确率；
- 统计误报样例；
- 统计漏报样例；
- 分析低光照、遮挡、小目标场景表现；
- 给出推荐置信度阈值；
- 给出推荐 NMS 阈值；
- 输出每类样本数、误报、漏报和典型失败图片；
- 输出模型评估报告。

## 建议目录

```text
dataset/
labels/
training/
models/
reports/
```

## 交付物

- 数据集；
- 标注文件；
- 标注规范；
- 训练代码或训练配置；
- `best.pt`；
- `best.onnx`；
- `classes.json`；
- `label.names`；
- `expected-output-v1.json`；
- 预处理和后处理说明；
- 类别映射说明；
- 模型评估报告。

## 验收标准

- 至少能识别 3 种设备或目标类别；
- 至少能识别 2 种外观异常或故障类别；
- 至少能识别 1 种环境异常；
- 模型可以导出为 ONNX；
- 成员1可以基于交付模型完成 Atlas 部署；
- 评估报告说明主要误报和漏报场景。
- Atlas 转换后同一测试图片的类别和检测框与开发机结果基本一致。

## 当前模型产物状态

当前仓库保留两条模型线：

- `edgeeye-detector-v1`：四类基线，包含绝缘子正常/破损和变压器正常/破损。
- `edgeeye-insulator-v1-opt30-yolov8s-adamw`：两类绝缘子优化候选，类别为
  `insulator_normal` 和 `insulator_surface_damage`。

两类候选模型导出的 YOLOv8 ONNX 输出为 `output0 [1,6,8400]`，不能直接套用
四类基线的 `[1,8,8400]` 后处理形状。优化结果和数据划分见
[`dataset/docs/edgeeye-insulator-v1-optimization-report.md`](../dataset/docs/edgeeye-insulator-v1-optimization-report.md)。
该候选模型是否替换四类基线，需要在 Atlas 转换和端到端联调前单独确认。
