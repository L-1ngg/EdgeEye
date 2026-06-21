# 成员1：Atlas 开发板与边缘推理

## 开发目标

负责摄像头、Atlas 开发板和模型部署，打通边缘端从视频读取到模型推理再到后端上传的完整链路。

成员1解决的问题：

```text
模型如何在开发板上运行，以及边缘端如何稳定输出检测结果。
```

## 职责范围

主负责：

- Atlas 开发板环境配置；
- 摄像头接入和视频流读取；
- 模型转换、部署和推理；
- 推理结果绘制与上传；
- 边缘端性能和稳定性测试。

协作内容：

- 使用成员2提供的目标检测模型和标签配置；
- 对接成员4提供的后端接口；
- 向成员5提供可展示的实时检测数据。

## 输入

- 成员2提供的目标检测模型；
- 成员2提供的 `classes.json` 和预处理参数；
- 成员2提供的 `best.pt`、`best.onnx`、`label.names` 和测试样例；
- 成员4提供的后端接口地址、字段格式和鉴权方式；
- 全组统一遵守 [数据契约与接口规范](./contracts.md)。

## 当前实测环境基线

以下信息来自 2026-06-18 对当前开发板镜像和外接 USB 摄像头的实测，用于成员之间联调对齐。后续更换镜像、开发板或摄像头时，需要重新确认本节。

### Atlas 与 CANN

| 项目 | 当前值 |
| --- | --- |
| 主机名 | `davinci-mini` |
| 系统 | `Ubuntu 22.04 LTS` |
| 架构 | `aarch64` |
| 内核 | `Linux 5.10.0+` |
| 设备树标识 | `Hisilicon PhosphorHi1910B evb` |
| Atlas 商业型号 | `Atlas 200I A2` |
| Product Name | `IT22MMDB` |
| NPU / Chip | `310B4` |
| `soc_version` | `Ascend310B4` |
| CANN / Ascend toolkit | `7.0.RC1`，版本文件显示 `7.0.0.5.242` |
| Firmware Version | `7.0.0.5.242` |
| `atc` 路径 | `/usr/local/Ascend/ascend-toolkit/7.0.RC1/aarch64-linux/bin/atc` |
| `ACL_DEVICE_ID` | `0` |
| NPU 设备节点 | `/dev/davinci0`、`/dev/davinci_manager` |
| pyACL 状态 | `acl.init()`、`acl.rt.get_device_count()`、`acl.rt.set_device(0)` 均可成功 |

当前镜像中未发现可直接用于本项目的 `.om` 目标检测模型文件。成员2仍需提供 ONNX/OM 模型、`classes.json`、`label.names`、输入尺寸和阈值参数。

## 当前模型接入壳子

2026-06-21 已补充一条开发机/临时联调用的 ONNX 接入壳子，用于在最终 Atlas OM/ACL 推理完成前打通“模型输出 → EdgeEye Detection → 后端上传”链路。

2026-06-22 成员2补充当前测试版模型信息：模型类型为 YOLOv8 `detect`，当前只有 1 类 `0: transformer`，输入尺寸为 `640x640`，推荐阈值为 `conf=0.25`、`iou=0.45`。该模型仅训练 3 轮，本阶段只用于跑通转换前的 ONNX 调试链路和后续 Atlas 转换/推理代码，不以识别准确率作为验收条件。

当前本地模型资产：

| 文件 | 用途 |
| --- | --- |
| `models/artifacts/detector-transformer-v1.onnx` | 当前一类 `transformer` YOLO detect ONNX 模型，本地大文件被 `.gitignore` 忽略 |
| `model-deploy/edge_onnx_bridge.py` | 开发机 ONNX 推理与后端 payload 生成脚本 |
| `model-deploy/classes-v1.json` | `class_id` 到 `category`、`deviceType`、`faultType` 的映射 |
| `model-deploy/label.names` | 类别顺序文件，当前只有 `transformer` |
| `model-deploy/preprocess-v1.json` | 输入尺寸、颜色通道、归一化、置信度阈值和 NMS 阈值 |
| `model-deploy/expected-output-v1.json` | 5 张本地测试图的 ONNX smoke 基准，用于后续 OM/ACL 输出对比 |
| `model-deploy/artifacts/transformer-v1-test-images/` | 本地 5 张测试图、标注图和 payload 输出，Git 忽略 |

当前模型只输出一类：

```json
{
  "category": "transformer",
  "deviceType": "transformer",
  "faultType": null
}
```

因此它只能先用于设备检测框展示，不会触发后端故障、告警或维修建议。若后续要产生故障事件，成员2需要交付可映射到 `faultType` 的类别，例如 `surface_damage`、`rust`、`foreign_object`、`smoke` 或 `fire`。

本地单图验证命令：

```bash
python3 model-deploy/edge_onnx_bridge.py \
  --image model-deploy/artifacts/transformer-v1-test-images/raw/transformer-v1-001.jpg \
  --frame-id frame-001 \
  --inspection-id inspection-transformer-v1-smoke \
  --annotated-output model-deploy/artifacts/transformer-v1-test-images/annotated/transformer-v1-001.jpg \
  --payload-output model-deploy/artifacts/transformer-v1-test-images/payloads/transformer-v1-001.json
```

后端已启动时可直接上传检测结果：

```bash
python3 model-deploy/edge_onnx_bridge.py \
  --image /path/to/image.jpg \
  --api-base http://localhost:8000/api \
  --start-inspection
```

注意：该脚本当前只上传 JSON 检测结果，不负责把图片文件上传到后端。真实联调时，`imageUrl` 和 `annotatedImageUrl` 必须指向后端可访问的 `/uploads/...` 路径。

正式板端路线仍然是：

```text
ONNX -> atc 转 OM -> Atlas ACL 加载 OM -> 同样生成 EdgeEye Detection payload
```

`edge_onnx_bridge.py` 的价值是固定预处理、后处理、类别映射和上传 payload 形状；后续更换模型时优先替换模型文件、`label.names`、`classes-v1.json` 和阈值配置，不重写后端上传契约。

### 摄像头

| 项目 | 当前值 |
| --- | --- |
| 摄像头型号 | `Alcor Micro Corp. PC Camera` |
| USB ID | `058f:1412` |
| 连接方式 | USB |
| 总线信息 | `usb-xhci-hcd.1.auto-1.1` |
| 驱动 | `uvcvideo` |
| 采集节点 | `/dev/video0` |
| 元数据节点 | `/dev/video1` |
| Media 节点 | `/dev/media0` |
| 支持格式 | `MJPG`、`YUYV` |
| 当前测试配置 | MJPG `640x480 @ 30 FPS` |
| 支持分辨率示例 | `640x480`、`800x600`、`1280x720`、`1280x960` |

测试截图和短视频保存在当前 Trellis 任务目录中：

- `.trellis/tasks/06-17-edge-atlas/camera-usb-video0-640x480.jpg`
- `.trellis/tasks/06-17-edge-atlas/camera-usb-video0-640x480-warmup.jpg`
- `.trellis/tasks/06-17-edge-atlas/camera-usb-video0-640x480-3s.mjpeg`

当前截图可证明 `/dev/video0` 能读帧，但画面几乎全黑。演示前需要将摄像头对准亮处或调整曝光后重新保存截图和视频。

## 输出

边缘端需要输出：

```text
摄像头画面
检测框
设备类别
故障类别
推理耗时
FPS
设备资源占用
```

检测结果示例：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "frameId": "frame-000001",
  "timestamp": "2026-06-16T10:00:00+08:00",
  "deviceId": "device-001",
  "imageWidth": 1280,
  "imageHeight": 720,
  "detections": [
    {
      "category": "insulator_defect",
      "deviceType": "insulator",
      "faultType": "surface_damage",
      "confidence": 0.91,
      "bbox": [120, 80, 360, 420]
    }
  ],
  "performance": {
    "latencyMs": 42,
    "fps": 18.5,
    "cpuUsage": 42.5,
    "memoryUsage": 61.2,
    "npuUsage": 38.4
  }
}
```

## 任务清单

### 环境准备

- 确认 Atlas 开发板型号；
- 确认系统版本；
- 确认 CANN 环境版本；
- 完成系统镜像烧录或环境恢复；
- 配置网络；
- 配置 SSH；
- 建立基础运行目录和配置文件。

### 摄像头接入

- 确认摄像头类型：USB 或 MIPI；
- 验证系统能识别摄像头；
- 实现单帧图片采集；
- 实现连续视频流读取；
- 保存测试截图和测试视频；
- 处理摄像头断开、读取失败和重连。

### 模型部署

- 参考 [`atlas-insulator-detection`](https://gitee.com/jerry12345555555/atlas-insulator-detection) 的 `best.pt -> ONNX -> ATC -> OM -> ACL` 路线；
- 跑通官方目标检测样例；
- 明确模型输入尺寸、颜色格式和归一化参数；
- 将成员2提供的 ONNX 模型转换为板端可运行格式；
- 输出 `atc` 转换命令，记录 `soc_version`、输入尺寸、输入 dtype 和 CANN 版本；
- 将 OM 模型、`label.names` 和推理脚本放在固定部署目录；
- 验证转换后模型推理结果是否与开发机一致；
- 输出模型转换命令和依赖说明。

### 实时推理

- 从摄像头读取帧；
- 按配置抽帧进行推理，不把视频流每帧都上传；
- 完成图像预处理：resize 到模型输入尺寸、BGR 转 RGB、归一化、HWC 转 CHW、增加 batch 维度；
- 使用 ACL 加载 OM 并调用模型推理；
- 解析 YOLO 输出，完成置信度过滤、坐标转换和 NMS；
- 绘制检测框、类别和置信度；
- 执行相似帧过滤和关键帧选择；
- 按 `POST /api/detection/results` 契约上传关键帧检测结果、图片路径和性能数据。

### 板端推理服务

- 推理服务启动时初始化 ACL 并加载 OM，进程内复用同一个模型实例；
- 提供本地健康检查接口，至少返回模型路径、类别文件、CANN/ACL 初始化状态；
- 单帧推理结果统一转换为 EdgeEye `Detection` 结构；
- 保存标注图到 `annotated/{inspectionId}/{frameId}.jpg`；
- 退出或异常时释放 OM、ACL context 和 device，避免重复加载时报错；
- 可提供临时 `/infer` 图片调试接口，但最终联调以上传 `/api/detection/results` 为准。

### 容错与性能

- 摄像头断线时给出错误状态；
- 模型加载失败时输出明确日志；
- ACL 错误码需要输出上下文，例如模型路径、输入 shape、buffer 字节数和 CANN 版本；
- 后端上传失败时支持重试或缓存；
- 上传前写入本地 outbox 队列，收到后端 ACK 后再标记已确认；
- 每个上传 payload 必须携带 `idempotencyKey`，默认 `{inspectionId}:{frameId}`；
- 统计推理延迟；
- 统计 FPS；
- 记录 CPU、NPU 和内存占用；
- 连续运行不少于 30 分钟进行稳定性测试。

### 上传契约

- 检测框坐标必须使用 `[x1, y1, x2, y2]` 像素坐标；
- 每次上传必须包含 `idempotencyKey`、`inspectionId`、`frameId`、`timestamp`、`imageWidth`、`imageHeight`；
- 上传必须标明 `isKeyFrame`、`uploadReason` 和 `sampleWindow`；
- 目标类别、故障类型、风险等级等枚举值必须使用 [数据契约与接口规范](./contracts.md) 中定义的值；
- 图片路径命名遵守 [工程规范与联调标准](./engineering-standards.md)；
- 后端不可用时至少保留最近一批待上传结果，避免联调时数据直接丢失。

### 关键帧策略

- 正常画面每秒最多上传一帧 `periodic_sample`；
- 新故障、新环境异常或系统状态变化时立即上传；
- 故障持续中每 5 秒最多上传一帧 `fault_updated`；
- 故障恢复时上传一帧 `fault_resolved`；
- 类别不变、检测框 IoU 大于 `0.9` 且风险状态不变时，判定为相似帧，不上传。

## 建议目录

```text
edge-app/
camera/
model-deploy/
config/
logs/
```

## 交付物

- Atlas 环境配置说明；
- 摄像头读取程序；
- 模型转换脚本或命令记录；
- OM 推理脚本或板端推理服务；
- 实时推理程序；
- 后端上传程序；
- 边缘端配置文件；
- 性能测试报告；
- 常见故障处理说明。

## 验收标准

- Atlas 可以读取摄像头画面；
- Atlas 可以运行至少一个目标检测模型；
- 检测结果包含类别、置信度和检测框；
- 可以将结果上传到后端；
- 能展示推理耗时和 FPS；
- 上传数据符合 `POST /api/detection/results` 契约；
- 摄像头断开或后端不可用时不会导致程序直接崩溃；
- 联调时能支撑前端实时展示。
