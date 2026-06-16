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
