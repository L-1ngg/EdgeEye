# 成员4：后端、数据库、报告与大模型维修建议接口

## 开发目标

负责系统的数据中心和业务服务，接收边缘端上传结果，保存巡检数据，生成告警、报告和大模型维修建议，并向前端提供查询接口。

成员4解决的问题：

```text
检测结果如何接收、保存、查询、告警、生成报告和调用大模型。
```

## 职责范围

主负责：

- 数据库设计；
- 后端 API；
- 图片和检测结果保存；
- 巡检记录查询；
- 故障和告警管理；
- Dashboard 统计；
- 大模型维修建议后端调用；
- 大模型 API Key 管理；
- 调用超时、失败和重试；
- 巡检报告生成。

协作内容：

- 接收成员1上传的边缘端结果；
- 使用成员3提供的规则和提示词；
- 向成员5提供前端所需接口；
- 反馈接口联调问题。

## 标准后端流程

```text
Atlas 上传检测结果
   ↓
后端保存原图、标注图和结构化结果
   ↓
查询成员3定义的规则
   ↓
生成风险等级和告警
   ↓
按需调用大模型
   ↓
保存大模型维修建议
   ↓
返回前端展示
```

## 数据库设计目标

建议至少包含以下表：

- 设备信息表；
- 巡检任务表；
- 检测结果表；
- 故障记录表；
- 告警表；
- 大模型维修建议表；
- 报告表。

关键约束：

- `inspection.inspectionId` 主键；
- `detection_result.idempotencyKey` 唯一；
- `detection_result (inspectionId, frameId)` 唯一；
- 未恢复故障事件中 `fault.eventKey` 唯一；
- `advice.faultId` 默认唯一，允许重生成时必须引入版本字段；
- `report (inspectionId, format, version)` 唯一；
- 告警去重使用 `dedupKey` 和处理状态约束，避免重复活跃告警。

## 核心接口

建议接口：

```text
GET  /api/health
GET  /api/system/status
GET  /api/camera/stream.mjpg
POST /api/inspection/start
POST /api/inspections/:id/finish
POST /api/inspections/:id/fail
POST /api/detection/results
POST /api/advice/generate
GET  /api/devices
GET  /api/inspections
GET  /api/inspections/:id/latest-result
GET  /api/faults
GET  /api/alarms
GET  /api/events
PATCH /api/faults/:id/status
PATCH /api/alarms/:id/status
GET  /api/dashboard
GET  /api/reports
GET  /api/reports/:id
GET  /api/reports/:id/export
GET  /api/faults/:id/advice
```

所有接口返回格式、错误格式、枚举值和核心数据结构见 [数据契约与接口规范](./contracts.md)。完整端点、查询参数和响应示例见 [API 端点规范](./api-spec.md)。

## 接口职责

### `POST /api/inspection/start`

用于创建一次巡检任务。

请求示例：

```json
{
  "deviceId": "device-001",
  "operator": "team",
  "source": "atlas"
}
```

返回示例：

```json
{
  "success": true,
  "data": {
    "inspectionId": "inspection-20260616-0001",
    "status": "running"
  },
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

巡检结束和失败接口用于维护 `Inspection.status`、`endedAt` 和报告生成时机，具体请求和响应见 [API 端点规范](./api-spec.md)。

### `POST /api/detection/results`

用于接收 Atlas 上传的识别结果。

请求示例：

```json
{
  "idempotencyKey": "inspection-20260616-0001:frame-000001",
  "inspectionId": "inspection-20260616-0001",
  "frameId": "frame-000001",
  "frameSeq": 1,
  "timestamp": "2026-06-16T10:00:00+08:00",
  "deviceId": "device-001",
  "isKeyFrame": true,
  "uploadReason": "periodic_sample",
  "eventKey": null,
  "imageUrl": "/uploads/raw/inspection-20260616-0001/frame-000001.jpg",
  "annotatedImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000001.jpg",
  "imageWidth": 1280,
  "imageHeight": 720,
  "detections": [
    {
      "category": "insulator_surface_damage",
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

成功返回示例：

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

说明：

- 上传请求体只接收原始检测结果、图片 URL 和性能数据。
- 后端负责根据规则生成 `Fault` 和 `Alarm`，Atlas 不直接上传故障记录。
- 后端必须按 `idempotencyKey` 幂等保存；重复请求不重复生成故障和告警。
- 同一事件按 `eventKey` 聚合，更新 `firstSeenAt`、`lastSeenAt`、`occurrenceCount` 和最佳证据帧。

### `POST /api/advice/generate`

用于根据故障记录生成大模型维修建议。

请求示例：

```json
{
  "faultId": "fault-000001"
}
```

返回示例：

```json
{
  "success": true,
  "data": {
    "adviceId": "advice-000001",
    "faultId": "fault-000001",
    "possibleCauses": ["机械冲击", "长期老化"],
    "riskAnalysis": "可能降低绝缘性能",
    "inspectionSteps": ["检查破损范围", "检查是否存在放电痕迹"],
    "maintenanceSuggestions": ["安排专业人员复检", "必要时更换绝缘子"],
    "safetyNotes": ["操作前确认设备状态", "维修建议需人工审核"],
    "modelName": "configured-llm",
    "createdAt": "2026-06-16T10:00:00+08:00"
  },
  "message": "ok",
  "timestamp": "2026-06-16T10:00:00+08:00"
}
```

### `GET /api/system/status`

用于 Dashboard 展示摄像头、Atlas、模型和后端状态。返回结构见 [数据契约与接口规范](./contracts.md) 中的 `SystemOverview`。

## 任务清单

### 数据服务

- 建立数据库；
- 完成数据表结构；
- 初始化测试设备数据；
- 保存原图；
- 保存标注图；
- 保存检测结果；
- 保存故障记录；
- 保存告警记录；
- 维护事件聚合字段；
- 维护告警去重字段。

### API 服务

- 实现巡检任务创建接口；
- 实现巡检结束和失败接口；
- 实现检测结果接收接口；
- 实现设备列表接口；
- 实现巡检记录接口；
- 实现最新巡检结果接口；
- 实现故障查询接口；
- 实现告警查询接口；
- 实现聚合事件查询接口；
- 实现故障和告警处理状态更新接口；
- 实现 Dashboard 统计接口；
- 实现系统状态接口；
- 实现报告查询和导出接口。

### 大模型维修建议

- 读取成员3提供的提示词模板；
- 读取成员3提供的规则文件；
- 生成大模型输入；
- 调用大模型；
- 解析 JSON 输出；
- 保存大模型维修建议结果；
- 处理超时；
- 处理失败重试；
- 防止 API Key 暴露到前端。

### 报告生成

- 按巡检任务生成报告；
- 巡检结束后触发报告生成，`inspection.status` 和 `reportStatus` 分开维护；
- 包含设备信息；
- 包含检测结果；
- 包含故障和告警；
- 包含大模型维修建议；
- 支持 HTML 或 PDF 输出；
- 报告生成失败时保存 `reportStatus: failed` 和错误信息，允许重试。

## 建议目录

```text
server/
database/
api-docs/
report-template/
uploads/
```

## 交付物

- 后端服务；
- 数据库结构；
- API 文档；
- 测试数据；
- 报告模板；
- 大模型维修建议接口；
- `docker-compose.yml`；
- 环境变量说明。
- 契约对齐说明，确认接口字段和 [数据契约与接口规范](./contracts.md) 一致。

## 验收标准

- 可以接收 Atlas 上传结果；
- 可以对重复上传做幂等处理；
- 可以保存检测结果、图片和性能数据；
- 可以将同一故障多帧聚合为一个事件；
- 可以生成故障和告警记录，并正确处理告警去重；
- 可以调用大模型维修建议接口并保存结果；
- 可以提供前端 Dashboard、巡检记录、故障、告警和报告数据；
- 可以提供 Dashboard 所需系统状态数据；
- 大模型密钥只在后端使用；
- 接口异常时返回明确错误信息。

## 后端联调补充约定

- 后端默认将 `EDGEEYE_UPLOADS_DIR` 挂载到 `/uploads`，将 `EDGEEYE_REPORTS_DIR` 挂载到 `/reports`，用于展示 Atlas 保存的原图、标注图和报告导出文件。
- `POST /api/detection/results` 仍然只接收 JSON；不要在该路径混用 multipart。
- 每个检测框必须满足 `0 <= x1 < x2 <= imageWidth` 和 `0 <= y1 < y2 <= imageHeight`；后端会在入口校验，越界返回 `VALIDATION_ERROR`。
- `performance.npuUsage` 可以为 `null`，用于表示 Atlas 板端当前无法读取 NPU 使用率。
