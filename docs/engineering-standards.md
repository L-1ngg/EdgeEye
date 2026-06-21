# 工程规范与联调标准

## 目标

本文档定义项目目录、命名、配置、日志、测试、交付和联调标准，用于保证 5 个成员的模块可以在两周内顺利集成。

## 推荐仓库结构

```text
.
├── docs/
├── edge-app/
├── camera/
├── model-deploy/
├── board-backend/
├── dataset/
├── labels/
├── training/
├── rules/
├── prompt-template/
├── server/
├── database/
├── web/
├── test-cases/
├── demo-data/
├── screenshots/
└── reports/
```

说明：

- `docs/` 存放项目文档和契约；
- `edge-app/` 存放 Atlas 边缘端主程序；
- `model-deploy/` 存放模型转换、部署脚本和板端模型；
- `board-backend/` 存放开发板本地推理服务和调试接口；
- `training/` 存放模型训练代码和配置；
- `rules/` 存放故障和告警规则；
- `prompt-template/` 存放大模型维修建议提示词模板；
- `server/` 存放后端服务；
- `web/` 存放前端应用；
- `demo-data/` 存放演示用图片、视频和模拟接口数据；
- `reports/` 存放评估报告、测试报告和最终巡检报告样例。

## 文件命名规范

### 图片和视频

```text
raw/{inspectionId}/{frameId}.jpg
annotated/{inspectionId}/{frameId}.jpg
videos/demo-{date}-{scene}.mp4
```

示例：

```text
raw/inspection-20260616-0001/frame-000001.jpg
annotated/inspection-20260616-0001/frame-000001.jpg
```

接口中的 URL 统一加 `/uploads/` 前缀，例如 `/uploads/raw/inspection-20260616-0001/frame-000001.jpg`。本节路径是存储目录相对路径。

### 模型文件

```text
models/artifacts/detector-v1.onnx
models/artifacts/detector-v1.om
models/artifacts/detector-v1.pt
model-deploy/label.names
model-deploy/classes-v1.json
model-deploy/preprocess-v1.json
```

大模型、数据集压缩包、训练权重和板端 `.om` 属于本地 artifacts，默认不进入 Git。仓库只提交目录占位、推理/转换脚本、类别映射、预处理配置和说明文档。

### 规则文件

```text
rules/fault-rules.json
rules/alarm-rules.json
prompt-template/advice-template.md
```

## 配置规范

各模块必须提供示例配置，不提交真实密钥。

推荐文件：

```text
.env.example
config/default.yaml
config/local.example.yaml
```

关键配置项：

| 配置项 | 说明 |
| --- | --- |
| `BACKEND_BASE_URL` | 后端接口地址 |
| `CAMERA_SOURCE` | 摄像头编号、视频文件或 RTSP 地址 |
| `MODEL_PATH` | 板端模型路径 |
| `MODEL_DIR` | OM、类别文件和模型配置目录 |
| `OM_MODEL_PATH` | OM 模型绝对路径，优先级高于 `MODEL_PATH` |
| `CLASSES_PATH` | 类别文件路径 |
| `LABEL_NAMES_PATH` | `label.names` 路径，顺序必须与训练类别一致 |
| `ACL_DEVICE_ID` | Atlas 推理设备 ID |
| `CONF_THRESHOLD` | 置信度阈值 |
| `IOU_THRESHOLD` | NMS IoU 阈值 |
| `UPLOAD_IMAGE_DIR` | 图片保存目录 |
| `EDGE_UPLOAD_MIN_INTERVAL_MS` | 正常状态关键帧最小上传间隔 |
| `EDGE_FAULT_UPDATE_INTERVAL_MS` | 故障持续中证据帧最小上传间隔 |
| `EDGE_FRAME_SIMILARITY_THRESHOLD` | 相似帧过滤阈值 |
| `EDGE_QUEUE_MAX_ITEMS` | 边缘端本地待上传队列最大条数 |
| `LLM_API_KEY` | 大模型密钥，仅后端使用 |
| `LLM_MODEL` | 大模型名称 |

## 日志规范

日志至少包含：

- 时间；
- 模块名；
- 日志等级；
- 事件名称；
- 关键 ID；
- 错误信息。

示例：

```json
{
  "timestamp": "2026-06-16T10:00:00+08:00",
  "level": "INFO",
  "module": "edge-app",
  "event": "detection_uploaded",
  "inspectionId": "inspection-20260616-0001",
  "frameId": "frame-000001",
  "latencyMs": 42
}
```

错误日志示例：

```json
{
  "timestamp": "2026-06-16T10:00:00+08:00",
  "level": "ERROR",
  "module": "server",
  "event": "advice_generation_failed",
  "faultId": "fault-000001",
  "error": "request timeout"
}
```

## 数据集规范

### 数据划分

建议比例：

- 训练集：70%;
- 验证集：20%;
- 测试集：10%。

### 标注要求

- 每张图片必须有唯一文件名；
- 检测框只框住可见目标；
- 小目标、遮挡和模糊样本需要在评估报告中单独说明；
- 类别名称必须和 `classes.json` 一致；
- 数据来源和样本数量必须记录在模型评估报告中。

### `classes.json` 示例

```json
{
  "version": "detector-v1",
  "classes": [
    {
      "id": 0,
      "name": "insulator_normal",
      "type": "device"
    },
    {
      "id": 1,
      "name": "insulator_surface_damage",
      "type": "fault"
    },
    {
      "id": 2,
      "name": "transformer_normal",
      "type": "device"
    },
    {
      "id": 3,
      "name": "transformer_surface_damage",
      "type": "fault"
    }
  ]
}
```

`type` 必须使用 [数据契约与接口规范](./contracts.md) 中的 `modelClassType` 枚举。`name` 必须能映射到 `deviceType` 或 `faultType`。
`classes.json` 必须包含 `version`，后端和前端展示模型版本时使用该值。
若后续新增 `bird_nest` 等专门类别，可以先映射为 `faultType: "foreign_object"`，
避免在模型试验阶段频繁扩展接口枚举。

### 推荐训练与部署主线

参考 [`atlas-insulator-detection`](https://gitee.com/jerry12345555555/atlas-insulator-detection) 的主线建议直接沿用到本项目：

```text
dataset.yaml + label.names
  ↓
train.py 训练得到 best.pt
  ↓
Ultralytics export 得到 best.onnx
  ↓
昇腾环境使用 atc 转成 detector-v1.om
  ↓
Atlas 开发板通过 ACL 加载 OM 推理
```

推荐第一版模型配置：

- 输入尺寸：`640x640`；
- batch：`1`；
- 导出 `opset`：`11`；
- 置信度阈值：`0.25`；
- NMS IoU 阈值：`0.45`。

板端推理预处理必须保持一致：

- BGR 转 RGB；
- resize 到模型输入尺寸；
- 归一化到 `[0, 1]`；
- HWC 转 CHW；
- 增加 batch 维度，最终输入 `NCHW`。

板端后处理必须包含：

- 置信度过滤；
- 坐标从模型输入空间映射回原图；
- NMS；
- 输出 `class_id`、`class_name`、`confidence`、`bbox`、`inference_ms` 和 `fps`。

Atlas 部署记录里必须保留：

- Atlas 开发板型号；
- CANN 版本；
- `atc` 命令；
- `soc_version`；
- OM 输入和输出 shape；
- `label.names` 与 `classes.json` 的一致性检查结果。

## 模型交付规范

成员2交给成员1时必须包含：

- ONNX 模型；
- `classes.json`；
- 输入尺寸；
- 颜色通道顺序；
- 归一化方式；
- NMS 阈值；
- 置信度阈值；
- 一组测试图片；
- 测试图片的期望输出。

推荐 `preprocess-v1.json`：

```json
{
  "inputWidth": 640,
  "inputHeight": 640,
  "colorFormat": "RGB",
  "normalize": {
    "mean": [0, 0, 0],
    "std": [255, 255, 255]
  },
  "confidenceThreshold": 0.25,
  "nmsThreshold": 0.45
}
```

模型交付还必须提供一份 `expected-output-v1.json`，至少包含 5 张测试图的期望 `category`、`bbox`、`confidence` 范围和类别映射结果，用于成员1在 Atlas 转换后做一致性验证。

### 当前 ONNX 调试桥

`model-deploy/edge_onnx_bridge.py` 是开发机和早期联调用的 ONNX 调试桥，职责是验证模型调用链路和后端 payload 形状：

```bash
python3 model-deploy/edge_onnx_bridge.py --image /path/to/image.jpg
```

后端启动后可以直接提交检测结果：

```bash
python3 model-deploy/edge_onnx_bridge.py \
  --image /path/to/image.jpg \
  --api-base http://localhost:8000/api \
  --start-inspection
```

约束：

- 脚本只上传 JSON payload，不上传图片文件本身；
- 输出 bbox 必须转换为原图像素坐标 `[x1, y1, x2, y2]`；
- 类别映射必须来自 `model-deploy/classes-v1.json`，不得靠字符串猜测；
- 模型没有检测结果时上传 `detections: []` 仍是合法状态；
- 当前 ONNX 调试桥不是最终 Atlas 推理实现，正式部署仍需 `ONNX -> OM -> ACL` 验证。

## 边缘端上传策略

边缘端必须实现关键帧上传，不能把视频流每帧都上传到后端。

推荐默认值：

| 项 | 默认值 |
| --- | --- |
| 正常状态上传间隔 | 1000 ms |
| 故障持续中上传间隔 | 5000 ms |
| 检测框相似 IoU 阈值 | 0.9 |
| 本地队列容量 | 最近 1000 条或按磁盘空间配置 |

上传流程：

```text
摄像头采集
  ↓
抽帧推理
  ↓
相似帧过滤
  ↓
生成关键帧 payload
  ↓
写入本地 outbox 队列
  ↓
后台上传
  ↓
收到 ACK 后标记已确认
```

边缘端本地队列至少包含：

```json
{
  "idempotencyKey": "inspection-20260616-0001:frame-000001",
  "inspectionId": "inspection-20260616-0001",
  "frameId": "frame-000001",
  "payloadPath": "queue/frame-000001.json",
  "status": "pending",
  "retryCount": 0,
  "nextRetryAt": "2026-06-16T10:00:05+08:00",
  "lastError": null
}
```

重试建议使用指数退避，失败后进入 `pending` 等待下次上传；超过最大重试次数后保留为 `dead`，不得静默删除。

## 规则文件规范

### `fault-rules.json`

```json
{
  "rules": [
    {
      "deviceType": "insulator",
      "faultType": "surface_damage",
      "minConfidence": 0.8,
      "riskLevel": "high",
      "alarmRequired": true,
      "alarmLevel": "warning",
      "priority": "P1"
    }
  ]
}
```

### `alarm-rules.json`

```json
{
  "dedupWindowSeconds": 300,
  "rules": [
    {
      "riskLevel": "critical",
      "alarmLevel": "critical",
      "requireManualReview": true
    },
    {
      "riskLevel": "high",
      "alarmLevel": "warning",
      "requireManualReview": true
    },
    {
      "riskLevel": "medium",
      "alarmLevel": "warning",
      "requireManualReview": false
    },
    {
      "riskLevel": "low",
      "alarmLevel": "info",
      "requireManualReview": false
    }
  ]
}
```

告警去重默认键为 `deviceId + faultType + alarmLevel`。如需修改，必须同步更新 [数据契约与接口规范](./contracts.md) 和后端接口测试。
去重命中时后端只更新 `lastTriggeredAt` 和 `suppressedCount`。

## API 联调规范

联调前成员4必须提供：

- 后端启动命令；
- `.env.example`；
- API 基础地址；
- 接口文档；
- `docs/openapi.yaml` 或等价可校验契约；
- 一份可直接导入的模拟数据；
- 健康检查接口。

建议健康检查：

```text
GET /api/health
GET /api/system/status
```

`GET /api/health` 返回示例：

```json
{
  "success": true,
  "data": {
    "status": "online",
    "version": "0.1.0"
  },
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

## 测试规范

### 成员1边缘端测试

- 摄像头读取测试；
- 单帧推理测试；
- 连续视频推理测试；
- OM 加载和释放测试；
- ONNX 与 OM 一致性测试；
- 后端上传测试；
- 断网或后端不可用测试；
- 30 分钟连续运行测试。

### 成员2模型测试

- 每类目标至少提供 5 张测试样例；
- 记录误报样例；
- 记录漏报样例；
- 输出推荐阈值；
- 验证 `dataset.yaml`、`classes.json` 和 `label.names` 顺序一致；
- 验证 ONNX 推理结果。

### 成员3规则与建议测试

- 故障规则触发样例；
- 告警规则触发样例；
- 规则模板降级样例；
- 大模型维修建议输出格式测试；
- 大模型失败降级测试。

### 成员4接口测试

- 检测结果上传成功；
- 重复上传返回幂等 ACK；
- 同一故障多帧聚合为一个事件；
- 告警去重窗口命中；
- 缺失字段返回错误；
- 故障和告警生成；
- 故障和告警处理状态更新；
- 大模型维修建议生成；
- Dashboard 统计；
- 报告生成和导出。

### 成员5前端测试

- Dashboard 正常状态；
- Dashboard 异常状态；
- 实时巡检展示检测框；
- 实时巡检展示关键帧、过期态和无帧态；
- 故障中心展示聚合事件；
- 故障中心展示大模型维修建议；
- 报告中心展示报告生成中、导出成功和导出失败；
- 后端接口失败时页面有明确提示。

## 联调准入清单

进入第 6-7 天联调前必须具备：

- 成员1可以读取摄像头或测试视频；
- 成员2提供第一版 `best.pt`、ONNX 模型、`classes.json`、`label.names` 和至少 5 张验证图；
- 成员1提供 OM 转换命令或第一版 OM 模型；
- 成员3提供第一版 `fault-rules.json`、`alarm-rules.json` 和大模型维修建议提示词；
- 成员4提供 `POST /api/detection/results`；
- 成员4提供 `POST /api/advice/generate` 或可演示的降级建议结果；
- 成员5提供实时巡检页面；
- 全组使用同一份数据契约。

## 最终验收清单

最终演示前必须确认：

- 摄像头或备用视频可用；
- Atlas 或备用推理脚本可运行；
- 后端服务可启动；
- 前端页面可访问；
- Dashboard 有统计和系统状态；
- 实时巡检有检测框、设备结果和故障结果；
- 故障中心有故障、告警和大模型维修建议；
- 报告中心有报告；
- 有备用图片、视频和模拟数据；
- 有操作文档和答辩 PPT。
