# 数据契约与接口规范

## 目标

本文档定义各模块之间的统一数据结构、字段命名、状态枚举和 API 返回格式。所有成员在开发、联调和测试时以本文档为准。

机器可校验的接口定义见 [OpenAPI 规范](./openapi.yaml)。当 Markdown 示例和 OpenAPI 不一致时，必须先修正文档和 OpenAPI，再修改实现。

## 基本约定

### 命名规范

- JSON 字段使用 `camelCase`。
- Python 内部变量可以使用 `snake_case`，但对外 JSON 必须转换为 `camelCase`。
- 类别、状态、风险等级等枚举值统一使用英文小写和下划线。
- 页面展示时再翻译为中文，不在接口中混用中英文枚举。

### 时间规范

- 所有时间字段使用 ISO 8601 字符串。
- 默认使用北京时间，格式示例：`2026-06-16T10:00:00+08:00`。
- 字段名统一使用 `timestamp`、`startedAt`、`endedAt`、`createdAt`、`updatedAt`。

### ID 规范

| 对象 | 格式示例 |
| --- | --- |
| 设备 | `device-001` |
| 巡检任务 | `inspection-20260616-0001` |
| 视频帧 | `frame-000001` |
| 检测结果 | `detection-000001` |
| 上传结果 | `result-000001` |
| 故障记录 | `fault-000001` |
| 告警记录 | `alarm-000001` |
| 维修建议 | `advice-000001` |
| 报告 | `report-20260616-0001` |

### 坐标规范

检测框 `bbox` 统一为像素坐标：

```json
[x1, y1, x2, y2]
```

约定：

- `x1`、`y1` 是左上角；
- `x2`、`y2` 是右下角；
- 坐标基于原始图像尺寸；
- 坐标值为整数；
- 需要同时提供 `imageWidth` 和 `imageHeight`，方便前端缩放绘制。

### 置信度规范

- `confidence` 取值范围为 `0` 到 `1`。
- 前端展示时可以转换为百分比。
- 目标检测默认阈值建议从 `0.5` 开始，最终由成员2评估后给出。
- 高风险告警建议使用单独规则判断，不只依赖置信度。

## 统一枚举

### 设备类型 `deviceType`

| 值 | 中文含义 |
| --- | --- |
| `meter` | 仪表 |
| `insulator` | 绝缘子 |
| `transformer` | 变压器 |
| `switchgear` | 开关柜 |
| `circuit_breaker` | 断路器 |
| `unknown` | 未知 |

### 故障类型 `faultType`

| 值 | 中文含义 |
| --- | --- |
| `surface_damage` | 表面破损 |
| `rust` | 锈蚀 |
| `foreign_object` | 异物 |
| `smoke` | 烟雾 |
| `fire` | 明火 |
| `person_intrusion` | 人员闯入 |
| `helmet_missing` | 未佩戴安全帽 |
| `unknown` | 未知 |

### 风险等级 `riskLevel`

| 值 | 中文含义 | 建议展示 |
| --- | --- | --- |
| `none` | 无风险 | 灰色 |
| `low` | 低风险 | 蓝色 |
| `medium` | 中风险 | 黄色 |
| `high` | 高风险 | 橙色 |
| `critical` | 严重风险 | 红色 |

### 告警等级 `alarmLevel`

| 值 | 中文含义 |
| --- | --- |
| `info` | 提示 |
| `warning` | 预警 |
| `critical` | 严重 |

默认映射：

| `riskLevel` | 默认 `alarmLevel` | 说明 |
| --- | --- | --- |
| `none` | 不生成告警 | 无风险 |
| `low` | `info` | 仅提示 |
| `medium` | `warning` | 预警 |
| `high` | `warning` | 高风险预警，需要人工复核 |
| `critical` | `critical` | 严重告警，优先处理 |

如果规则文件要覆盖默认映射，必须同步更新 [工程规范与联调标准](./engineering-standards.md) 中的 `alarm-rules.json` 示例和后端测试数据。

### 处理状态 `processStatus`

| 值 | 中文含义 |
| --- | --- |
| `pending` | 待处理 |
| `processing` | 处理中 |
| `resolved` | 已处理 |
| `ignored` | 已忽略 |

### 系统状态 `systemStatus`

| 值 | 中文含义 |
| --- | --- |
| `online` | 在线 |
| `offline` | 离线 |
| `degraded` | 部分异常 |
| `error` | 错误 |
| `unknown` | 未知 |

### 巡检状态 `inspectionStatus`

| 值 | 中文含义 |
| --- | --- |
| `pending` | 待开始 |
| `running` | 运行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

### 巡检来源 `inspectionSource`

| 值 | 中文含义 |
| --- | --- |
| `atlas` | Atlas 边缘端 |
| `web` | 前端手动创建 |
| `mock` | 演示或测试模拟数据 |

### 处理优先级 `priority`

| 值 | 中文含义 |
| --- | --- |
| `P0` | 最高优先级，立即处理 |
| `P1` | 高优先级，尽快处理 |
| `P2` | 中优先级，计划处理 |
| `P3` | 低优先级，观察或记录 |

### 模型类别类型 `modelClassType`

用于 `classes.json` 中的 `type` 字段。

| 值 | 中文含义 |
| --- | --- |
| `device` | 设备类目标 |
| `fault` | 设备外观故障 |
| `environment` | 环境异常 |

### 上传原因 `uploadReason`

用于说明边缘端为什么选择上传当前帧。边缘端可以连续采集和推理，但只上传关键帧或事件帧。

| 值 | 中文含义 |
| --- | --- |
| `periodic_sample` | 周期采样帧 |
| `fault_started` | 故障首次出现 |
| `fault_updated` | 故障持续中且达到更新间隔 |
| `fault_resolved` | 故障消失或恢复 |
| `manual_capture` | 人工抓拍 |
| `system_event` | 系统状态变化 |

### 结果状态 `resultStatus`

| 值 | 中文含义 |
| --- | --- |
| `ready` | 已有可展示结果 |
| `processing` | 正在处理 |
| `stale` | 结果已过期 |
| `no_frame` | 尚无帧结果 |
| `failed` | 结果生成失败 |

### 事件状态 `eventStatus`

| 值 | 中文含义 |
| --- | --- |
| `new` | 新事件 |
| `ongoing` | 持续中 |
| `resolved` | 已恢复 |

### 建议状态 `adviceStatus`

| 值 | 中文含义 |
| --- | --- |
| `none` | 未生成 |
| `generating` | 生成中 |
| `ready` | 已生成 |
| `fallback` | 使用规则模板降级生成 |
| `failed` | 生成失败 |

### 报告状态 `reportStatus`

| 值 | 中文含义 |
| --- | --- |
| `pending` | 待生成 |
| `generating` | 生成中 |
| `ready` | 可查看或下载 |
| `failed` | 生成失败 |

### 数据新鲜度 `dataFreshness`

| 值 | 中文含义 |
| --- | --- |
| `fresh` | 数据新鲜 |
| `stale` | 数据过期 |
| `offline` | 数据源离线 |

### 页面状态 `pageState`

| 值 | 中文含义 |
| --- | --- |
| `loading` | 加载中 |
| `ready` | 可展示 |
| `empty` | 无数据 |
| `stale` | 有旧数据但已过期 |
| `partial_error` | 部分接口失败 |
| `error` | 页面不可用 |

## 幂等、关键帧和事件聚合约定

### 上传幂等

- `POST /api/detection/results` 必须携带 `idempotencyKey`。
- 默认格式为 `{inspectionId}:{frameId}`，例如 `inspection-20260616-0001:frame-000001`。
- 后端必须对 `idempotencyKey` 建唯一约束。
- 同一 `idempotencyKey` 且请求内容一致时，后端返回同一个 `resultId`，并设置 `duplicate: true`。
- 同一 `idempotencyKey` 但请求内容不一致时，后端返回 `IDEMPOTENCY_CONFLICT`，不得覆盖已有结果。
- 后端不得因为重复上传而重复生成 `Fault`、`Alarm`、`Advice` 或报告。

### 关键帧上传

边缘端可以连续采集和推理，但不得默认每帧上传。推荐策略：

- 正常状态每 1 秒最多上传 1 张 `periodic_sample`；
- 新故障或系统状态变化时立即上传；
- 故障持续中每 5 秒最多上传 1 张 `fault_updated`；
- 故障恢复后上传 1 张 `fault_resolved`；
- 相邻帧检测类别不变、检测框 IoU 大于 `0.9` 且风险状态不变时，可以过滤不上传。

### 事件聚合

- 后端按 `eventKey` 聚合同一业务事件。
- 默认 `eventKey` 为 `{inspectionId}:{deviceId}:{faultType}`，无法确认设备时可使用 `{inspectionId}:unknown:{faultType}:{zone}`。
- 同一 `eventKey` 的连续检测结果更新同一条 `Fault` 的 `lastSeenAt`、`occurrenceCount`、`lastConfidence` 和最佳证据帧字段。
- `bestFrameId` 默认选择同一事件中 `riskLevel` 最高、若相同则 `confidence` 最高的帧。
- `fault_resolved` 或后端超时判定恢复时，将事件状态置为 `resolved`，并更新 `processStatus`。

## API 响应格式

### 成功响应

所有后端接口成功时统一返回：

```json
{
  "success": true,
  "data": {},
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

列表接口返回：

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "pageSize": 20
  },
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

### 错误响应

所有后端接口失败时统一返回：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "invalid request payload",
    "details": {}
  },
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

常用错误码：

| 错误码 | 含义 |
| --- | --- |
| `VALIDATION_ERROR` | 请求字段缺失或格式错误 |
| `NOT_FOUND` | 数据不存在 |
| `UPLOAD_FAILED` | 图片或结果上传失败 |
| `MODEL_RESULT_INVALID` | 模型结果格式错误 |
| `ADVICE_GENERATION_FAILED` | 维修建议生成失败 |
| `SERVICE_UNAVAILABLE` | 后端服务不可用 |
| `DUPLICATE_UPLOAD` | 重复上传，后端已按幂等规则处理 |
| `IDEMPOTENCY_CONFLICT` | 同一幂等键对应不同请求内容 |
| `INSPECTION_NOT_RUNNING` | 巡检任务不在运行状态 |
| `INVALID_STATE_TRANSITION` | 状态流转不合法 |
| `RESULT_NOT_READY` | 最新结果尚未生成 |
| `RESULT_STALE` | 最新结果已过期 |
| `ADVICE_NOT_READY` | 维修建议仍在生成 |
| `REPORT_GENERATING` | 报告仍在生成 |
| `REPORT_EXPORT_FAILED` | 报告导出失败 |
| `UPSTREAM_TIMEOUT` | 上游模块超时 |
| `INTERNAL_ERROR` | 未分类内部错误 |

HTTP 状态码建议：

| 场景 | HTTP 状态码 |
| --- | --- |
| 字段校验失败 | `400` |
| 数据不存在 | `404` |
| 幂等键冲突或非法状态流转 | `409` |
| 模型结果、规则结果或图片 URL 无法处理 | `422` |
| 上游或后端服务暂不可用 | `503` |
| 未分类服务错误 | `500` |

## 核心数据结构

### 设备 `Device`

```json
{
  "deviceId": "device-001",
  "deviceName": "2号线路绝缘子",
  "deviceType": "insulator",
  "location": "2号线路A相",
  "status": "online",
  "createdAt": "2026-06-16T10:00:00+08:00",
  "updatedAt": "2026-06-16T10:00:00+08:00"
}
```

### 巡检任务 `Inspection`

```json
{
  "inspectionId": "inspection-20260616-0001",
  "deviceId": "device-001",
  "operator": "team",
  "source": "atlas",
  "status": "running",
  "startedAt": "2026-06-16T10:00:00+08:00",
  "endedAt": null
}
```

### 检测目标 `Detection`

```json
{
  "detectionId": "detection-000001",
  "category": "insulator_defect",
  "deviceType": "insulator",
  "faultType": "surface_damage",
  "confidence": 0.91,
  "bbox": [120, 80, 360, 420],
  "imageWidth": 1280,
  "imageHeight": 720
}
```

说明：

- `category` 是模型原始类别；
- `deviceType` 用于设备类目标；
- `faultType` 用于故障或环境异常类目标；
- 如果无法映射，使用 `unknown` 或 `null`，不要临时新增未登记枚举。
- `detectionId` 由后端保存后生成；Atlas 上传时不需要提供。
- Atlas 上传时 `deviceType` 和 `faultType` 至少有一个非空；纯设备目标填写 `deviceType`，故障或环境异常目标填写 `faultType`。
- `bbox` 必须满足 `0 <= x1 < x2 <= imageWidth`、`0 <= y1 < y2 <= imageHeight`。
- 后端会在 `POST /api/detection/results` 入口校验 `bbox` 是否越界；越界请求返回统一错误响应 `VALIDATION_ERROR`，不会写入检测结果、故障或告警。

### 故障记录 `Fault`

```json
{
  "faultId": "fault-000001",
  "inspectionId": "inspection-20260616-0001",
  "deviceId": "device-001",
  "deviceType": "insulator",
  "faultType": "surface_damage",
  "confidence": 0.91,
  "riskLevel": "high",
  "alarmRequired": true,
  "alarmLevel": "warning",
  "priority": "P1",
  "processStatus": "pending",
  "eventKey": "inspection-20260616-0001:device-001:surface_damage",
  "eventStatus": "ongoing",
  "firstSeenAt": "2026-06-16T10:00:00+08:00",
  "lastSeenAt": "2026-06-16T10:00:08+08:00",
  "occurrenceCount": 6,
  "lastConfidence": 0.88,
  "maxConfidence": 0.91,
  "bestFrameId": "frame-000021",
  "bestImageUrl": "/uploads/raw/inspection-20260616-0001/frame-000021.jpg",
  "bestAnnotatedImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000021.jpg",
  "location": "2号线路A相",
  "createdAt": "2026-06-16T10:00:00+08:00"
}
```

生成规则：

- `Fault` 由后端基于 `Detection` 和规则文件统一生成并保存。
- Atlas 不直接上传 `Fault`，除非后续明确扩展上传契约。
- `alarmLevel` 必须遵守本文档的 `riskLevel` 默认映射，或遵守已登记的 `alarm-rules.json` 覆盖规则。
- 同一 `eventKey` 下的连续帧不新建故障，只更新聚合字段。

### 告警记录 `Alarm`

```json
{
  "alarmId": "alarm-000001",
  "faultId": "fault-000001",
  "deviceId": "device-001",
  "alarmLevel": "warning",
  "riskLevel": "high",
  "message": "绝缘子表面破损，建议尽快复检",
  "processStatus": "pending",
  "dedupKey": "device-001:surface_damage:warning",
  "firstTriggeredAt": "2026-06-16T10:00:00+08:00",
  "lastTriggeredAt": "2026-06-16T10:00:08+08:00",
  "suppressedCount": 5,
  "reopenCount": 0,
  "createdAt": "2026-06-16T10:00:00+08:00"
}
```

生成规则：

- `Alarm` 由后端从 `Fault` 派生。
- 默认情况下 `riskLevel: none` 不生成告警，其余风险等级按告警规则决定。
- 告警去重默认键为 `deviceId + faultType + alarmLevel`，在 `dedupWindowSeconds` 时间窗口内只保留一条未处理告警。
- 去重命中时不新建告警，只更新 `lastTriggeredAt` 和 `suppressedCount`。

### 大模型维修建议 `Advice`

```json
{
  "adviceId": "advice-000001",
  "faultId": "fault-000001",
  "possibleCauses": ["机械冲击", "长期老化"],
  "riskAnalysis": "可能降低绝缘性能",
  "inspectionSteps": ["检查破损范围", "检查是否存在放电痕迹"],
  "maintenanceSuggestions": ["安排专业人员复检", "必要时更换绝缘子"],
  "safetyNotes": ["操作前确认设备状态", "维修建议需人工审核"],
  "modelName": "configured-llm",
  "adviceStatus": "ready",
  "createdAt": "2026-06-16T10:00:00+08:00"
}
```

`POST /api/advice/generate` 和 `GET /api/faults/:id/advice` 的 `data` 都返回完整 `Advice` 结构。大模型失败但规则模板可用时，仍返回完整 `Advice`，`modelName` 填写 `rule-template`。

### 系统状态 `SystemOverview`

```json
{
  "camera": {
    "status": "online",
    "lastFrameAt": "2026-06-16T10:00:00+08:00",
    "lastHeartbeatAt": "2026-06-16T10:00:02+08:00",
    "message": "camera stream is healthy",
    "degradedReason": null
  },
  "atlas": {
    "status": "online",
    "cpuUsage": 42.5,
    "memoryUsage": 61.2,
    "npuUsage": 38.4,
    "lastHeartbeatAt": "2026-06-16T10:00:02+08:00",
    "message": "edge app is uploading key frames",
    "degradedReason": null
  },
  "model": {
    "status": "online",
    "modelVersion": "detector-v1",
    "fps": 18.5,
    "latencyMs": 42,
    "lastHeartbeatAt": "2026-06-16T10:00:02+08:00",
    "message": "model inference is healthy",
    "degradedReason": null
  },
  "backend": {
    "status": "online",
    "lastHeartbeatAt": "2026-06-16T10:00:02+08:00",
    "message": "api and database are healthy",
    "degradedReason": null
  },
  "updatedAt": "2026-06-16T10:00:02+08:00",
  "dataFreshness": "fresh",
  "activeInspectionCount": 1,
  "unresolvedFaultCount": 1,
  "unresolvedAlarmCount": 1
}
```

## Atlas 上传检测结果

`POST /api/detection/results` 请求体：

当前最小联调方案采用“Atlas 或边缘程序先保存图片，再上传可访问 URL”的方式。后端必须能访问 `imageUrl` 和 `annotatedImageUrl`。若后续改为 multipart 上传，必须新增接口或更新 [API 端点规范](./api-spec.md)，不能在同一路径下混用两种请求格式。

```json
{
  "idempotencyKey": "inspection-20260616-0001:frame-000001",
  "inspectionId": "inspection-20260616-0001",
  "frameId": "frame-000001",
  "frameSeq": 1,
  "timestamp": "2026-06-16T10:00:00+08:00",
  "receivedAt": "2026-06-16T10:00:01+08:00",
  "deviceId": "device-001",
  "isKeyFrame": true,
  "uploadReason": "periodic_sample",
  "eventKey": null,
  "sampleWindow": {
    "startedAt": "2026-06-16T10:00:00+08:00",
    "endedAt": "2026-06-16T10:00:01+08:00",
    "frameCount": 5
  },
  "imageUrl": "/uploads/raw/inspection-20260616-0001/frame-000001.jpg",
  "annotatedImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000001.jpg",
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

说明：`performance.npuUsage` 在 Atlas 板端无法读取 NPU 指标时可以为 `null`；后端会保存该值并在系统状态接口中原样返回。

后端成功响应：

```json
{
  "success": true,
  "data": {
    "resultId": "result-000001",
    "inspectionId": "inspection-20260616-0001",
    "frameId": "frame-000001",
    "accepted": true,
    "duplicate": false,
    "processedAt": "2026-06-16T10:00:01+08:00",
    "inspectionStatus": "running",
    "faultsCreated": 1,
    "faultsUpdated": 0,
    "alarmsCreated": 1,
    "alarmsSuppressed": 0,
    "reportTriggered": false,
    "warnings": []
  },
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

保存后的最新巡检结果可以通过 `GET /api/inspections/:id/latest-result` 查询。该查询结果可以包含后端生成的 `faults`，但上传请求体不得包含 `faults`。

`GET /api/inspections/:id/latest-result` 额外返回：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "inspectionStatus": "running",
  "resultStatus": "ready",
  "isKeyFrame": true,
  "uploadReason": "fault_started",
  "eventKey": "inspection-20260616-0001:device-001:smoke",
  "eventStatus": "new",
  "receivedAt": "2026-06-16T10:00:01+08:00",
  "staleAfterMs": 3000
}
```

前端判断当前时间超过 `receivedAt + staleAfterMs` 时，应展示 `stale` 状态而不是继续当作实时数据。

### 故障中心事件项 `EventItem`

故障中心优先展示后端聚合后的事件项，避免前端自行拼接 `Fault`、`Alarm` 和 `Advice`。

```json
{
  "eventId": "event-000001",
  "eventType": "fault",
  "inspectionId": "inspection-20260616-0001",
  "deviceId": "device-001",
  "deviceName": "2号线路绝缘子",
  "faultId": "fault-000001",
  "alarmId": "alarm-000001",
  "faultType": "surface_damage",
  "riskLevel": "high",
  "alarmLevel": "warning",
  "processStatus": "pending",
  "title": "绝缘子表面破损",
  "summary": "同一故障持续出现 6 次，已保留最佳证据帧。",
  "occurrenceCount": 6,
  "firstOccurredAt": "2026-06-16T10:00:00+08:00",
  "lastOccurredAt": "2026-06-16T10:00:08+08:00",
  "latestFrameId": "frame-000021",
  "latestImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000021.jpg",
  "adviceStatus": "ready"
}
```

### 报告导出 `ReportExport`

```json
{
  "format": "pdf",
  "exportStatus": "ready",
  "downloadUrl": "/reports/report-20260616-0001.pdf",
  "fileName": "report-20260616-0001.pdf",
  "generatedAt": "2026-06-16T10:20:00+08:00",
  "expiresAt": null
}
```

### 巡检生命周期

巡检任务状态由后端维护：

```text
pending -> running -> completed
pending -> running -> failed
pending -> cancelled
```

状态规则：

- `POST /api/inspection/start` 创建任务后默认进入 `running`。
- 后端连续收到检测结果时保持 `running`。
- 后端收到结束请求后进入 `completed`。
- 报告生成状态使用 `reportStatus`，不要用 `inspectionStatus` 代替。
- 边缘端异常、模型失败或超过后端配置的超时时间无结果时可进入 `failed`。
- 前端或测试脚本取消未开始任务时进入 `cancelled`。

结束巡检使用 `POST /api/inspections/:id/finish`，失败巡检使用 `POST /api/inspections/:id/fail`。接口细节见 [API 端点规范](./api-spec.md)。

## 前端页面数据契约

### Dashboard

需要接口：

- `GET /api/dashboard`
- `GET /api/system/status`

必须展示：

- 设备数；
- 巡检数；
- 故障数；
- 告警数；
- 摄像头状态；
- Atlas 状态；
- 模型状态；
- 后端状态；
- 最近一次巡检时间；
- 最新高风险告警。
- 数据新鲜度；
- 未处理故障数和未处理告警数。

### 实时巡检

需要接口：

- `GET /api/inspections/:id/latest-result`
- 可选：`GET /api/system/status`

必须展示：

- 原图或标注图；
- 检测框；
- 类别和置信度；
- 设备识别结果；
- 实时故障和风险等级；
- FPS 和推理延迟；
- 当前结果状态 `resultStatus`；
- 是否关键帧 `isKeyFrame`；
- 上传原因 `uploadReason`；
- 数据过期状态。

### 故障中心

需要接口：

- `GET /api/faults`
- `GET /api/alarms`
- `GET /api/events`
- `POST /api/advice/generate`
- `GET /api/faults/:id/advice`

必须展示：

- 故障类别；
- 风险等级；
- 告警等级；
- 处理状态；
- 原因分析；
- 巡检步骤；
- 维修建议；
- 安全提示；
- 事件持续时间、出现次数和最佳证据帧；
- 建议生成状态。

### 报告中心

需要接口：

- `GET /api/reports`
- `GET /api/reports/:id`

必须展示：

- 巡检时间；
- 设备信息；
- 检测结果；
- 故障和告警；
- 大模型维修建议；
- 报告状态；
- 报告导出入口；
- 导出生成中、失败和可下载状态。

所有前端页面统一使用 `pageState` 表达加载、空态、过期、部分失败和错误状态。
