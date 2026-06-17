# API 端点规范

## 基本约定

- Base URL 示例：`http://localhost:8000`
- API 前缀：`/api`
- 请求和响应均使用 JSON。
- 当前最小联调方案中，图片由 Atlas 或边缘程序先保存为后端可访问 URL，再在 JSON 中提交。不要在 `POST /api/detection/results` 上混用 multipart。
- 后端默认将 `EDGEEYE_UPLOADS_DIR` 挂载到 `/uploads`，将 `EDGEEYE_REPORTS_DIR` 挂载到 `/reports`。Atlas 可以按 `/uploads/raw/{inspectionId}/{frameId}.jpg` 和 `/uploads/annotated/{inspectionId}/{frameId}.jpg` 生成可展示 URL。
- `performance.npuUsage` 在板端 NPU 指标不可读时可以为 `null`。
- 后端会校验每个 `bbox` 是否满足 `0 <= x1 < x2 <= imageWidth` 和 `0 <= y1 < y2 <= imageHeight`，越界返回 `VALIDATION_ERROR`。
- 成功和错误响应格式遵守 [数据契约与接口规范](./contracts.md)。
- 时间、枚举、ID 和字段命名遵守 [数据契约与接口规范](./contracts.md)。
- 机器可校验定义见 [OpenAPI 规范](./openapi.yaml)。

## 接口总览

| 方法 | 路径 | 使用方 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 全组 | 后端健康检查 |
| `GET` | `/api/system/status` | 前端 | Dashboard 系统状态 |
| `POST` | `/api/inspection/start` | Atlas/前端 | 创建巡检任务 |
| `POST` | `/api/inspections/:id/finish` | Atlas/前端 | 结束巡检任务 |
| `POST` | `/api/inspections/:id/fail` | Atlas/前端 | 标记巡检失败 |
| `GET` | `/api/inspections` | 前端 | 巡检记录列表 |
| `GET` | `/api/inspections/:id/latest-result` | 前端 | 获取某次巡检最新结果 |
| `POST` | `/api/detection/results` | Atlas | 上传检测结果 |
| `GET` | `/api/devices` | 前端 | 设备列表 |
| `GET` | `/api/faults` | 前端 | 故障列表 |
| `GET` | `/api/alarms` | 前端 | 告警列表 |
| `GET` | `/api/events` | 前端 | 故障中心聚合事件列表 |
| `PATCH` | `/api/faults/:id/status` | 前端 | 更新故障处理状态 |
| `PATCH` | `/api/alarms/:id/status` | 前端 | 更新告警处理状态 |
| `GET` | `/api/dashboard` | 前端 | Dashboard 统计 |
| `POST` | `/api/advice/generate` | 前端/后端 | 生成大模型维修建议 |
| `GET` | `/api/faults/:id/advice` | 前端 | 获取故障维修建议 |
| `GET` | `/api/reports` | 前端 | 报告列表 |
| `GET` | `/api/reports/:id` | 前端 | 报告详情 |
| `GET` | `/api/reports/:id/export` | 前端 | 报告导出 |

## `GET /api/health`

用于确认后端服务是否可用。

响应 `data`：

```json
{
  "status": "online",
  "version": "0.1.0"
}
```

## `GET /api/system/status`

用于 Dashboard 展示系统状态。

响应 `data` 使用 [数据契约与接口规范](./contracts.md) 中的 `SystemOverview`。

## `POST /api/inspection/start`

用于创建巡检任务。

请求：

```json
{
  "deviceId": "device-001",
  "operator": "team",
  "source": "atlas"
}
```

响应 `data`：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "status": "running"
}
```

## `GET /api/inspections`

用于巡检记录列表。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码，默认 `1` |
| `pageSize` | 否 | 每页数量，默认 `20` |
| `status` | 否 | 巡检状态 |
| `deviceId` | 否 | 设备 ID |

响应 `data.items[]`：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "deviceId": "device-001",
  "deviceName": "1号线路电压表",
  "status": "completed",
  "startedAt": "2026-06-16T10:00:00+08:00",
  "endedAt": "2026-06-16T10:10:00+08:00",
  "faultCount": 1,
  "alarmCount": 1
}
```

## `POST /api/inspections/:id/finish`

用于结束一次巡检任务。后端结束任务后可同步生成或异步触发报告。

请求：

```json
{
  "endedAt": "2026-06-16T10:10:00+08:00",
  "summary": "巡检正常结束"
}
```

响应 `data`：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "status": "completed",
  "endedAt": "2026-06-16T10:10:00+08:00"
}
```

## `POST /api/inspections/:id/fail`

用于标记巡检失败。

请求：

```json
{
  "endedAt": "2026-06-16T10:10:00+08:00",
  "reason": "camera disconnected"
}
```

响应 `data`：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "status": "failed",
  "endedAt": "2026-06-16T10:10:00+08:00"
}
```

## `GET /api/inspections/:id/latest-result`

用于实时巡检页面获取最新检测结果。

响应 `data`：

```json
{
  "inspectionId": "inspection-20260616-0001",
  "inspectionStatus": "running",
  "resultStatus": "ready",
  "frameId": "frame-000001",
  "frameSeq": 1,
  "timestamp": "2026-06-16T10:00:00+08:00",
  "receivedAt": "2026-06-16T10:00:01+08:00",
  "staleAfterMs": 3000,
  "isKeyFrame": true,
  "uploadReason": "periodic_sample",
  "eventKey": null,
  "eventStatus": null,
  "imageUrl": "/uploads/raw/inspection-20260616-0001/frame-000001.jpg",
  "annotatedImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000001.jpg",
  "imageWidth": 1280,
  "imageHeight": 720,
  "detections": [],
  "faults": [],
  "performance": {
    "latencyMs": 42,
    "fps": 18.5,
    "cpuUsage": 42.5,
    "memoryUsage": 61.2,
    "npuUsage": 38.4
  }
}
```

说明：

- `faults` 是后端根据检测结果和规则生成的 `Fault` 列表。
- Atlas 上传 `POST /api/detection/results` 时不得提交 `faults`。
- `resultStatus: stale` 表示可以展示旧数据，但必须提示实时结果已过期。
- `resultStatus: no_frame` 表示巡检已开始但还没有任何可展示帧。

## `POST /api/detection/results`

用于 Atlas 上传检测结果。请求体见 [数据契约与接口规范](./contracts.md) 的“Atlas 上传检测结果”。

请求必须包含 `idempotencyKey`。同一 `idempotencyKey` 重复上传且内容一致时，后端返回原 `resultId` 并设置 `duplicate: true`；同键不同内容返回 `IDEMPOTENCY_CONFLICT`。

响应 `data`：

```json
{
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
}
```

## `GET /api/devices`

用于获取设备列表，主要作为 Dashboard 和筛选条件数据源，不单独开发设备管理页面。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `deviceType` | 否 | 设备类型 |
| `status` | 否 | 系统状态 |

响应 `data.items[]` 使用 [数据契约与接口规范](./contracts.md) 中的 `Device`。

## `GET /api/faults`

用于故障中心展示故障列表。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码 |
| `pageSize` | 否 | 每页数量 |
| `riskLevel` | 否 | 风险等级 |
| `processStatus` | 否 | 处理状态 |
| `deviceId` | 否 | 设备 ID |

响应 `data.items[]` 使用 [数据契约与接口规范](./contracts.md) 中的 `Fault`。

## `GET /api/alarms`

用于故障中心展示告警列表。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码 |
| `pageSize` | 否 | 每页数量 |
| `alarmLevel` | 否 | 告警等级 |
| `processStatus` | 否 | 处理状态 |

响应 `data.items[]`：

使用 [数据契约与接口规范](./contracts.md) 中的 `Alarm`。

## `GET /api/events`

用于故障中心展示后端聚合事件，避免前端自行拼接故障、告警和建议状态。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码 |
| `pageSize` | 否 | 每页数量 |
| `riskLevel` | 否 | 风险等级 |
| `processStatus` | 否 | 处理状态 |
| `adviceStatus` | 否 | 维修建议状态 |

响应 `data.items[]` 使用 [数据契约与接口规范](./contracts.md) 中的 `EventItem`。

## `PATCH /api/faults/:id/status`

用于更新故障处理状态。

请求：

```json
{
  "processStatus": "resolved",
  "operator": "team",
  "note": "现场复检完成"
}
```

响应 `data` 使用 [数据契约与接口规范](./contracts.md) 中的 `Fault`。

## `PATCH /api/alarms/:id/status`

用于更新告警处理状态。

请求：

```json
{
  "processStatus": "resolved",
  "operator": "team",
  "note": "已通知维护人员"
}
```

响应 `data` 使用 [数据契约与接口规范](./contracts.md) 中的 `Alarm`。

## `GET /api/dashboard`

用于 Dashboard 统计。

响应 `data`：

```json
{
  "deviceCount": 5,
  "inspectionCount": 12,
  "faultCount": 3,
  "alarmCount": 2,
  "criticalAlarmCount": 1,
  "latestInspectionAt": "2026-06-16T10:00:00+08:00",
  "latestHighRiskAlarm": {
    "alarmId": "alarm-000001",
    "faultId": "fault-000001",
    "deviceName": "2号线路绝缘子",
    "faultType": "surface_damage",
    "riskLevel": "high",
    "alarmLevel": "warning"
  }
}
```

## `POST /api/advice/generate`

用于生成大模型维修建议。

请求：

```json
{
  "faultId": "fault-000001"
}
```

响应 `data`：

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
  "createdAt": "2026-06-16T10:00:00+08:00"
}
```

## `GET /api/faults/:id/advice`

用于获取已保存的故障维修建议。

响应 `data` 使用 [数据契约与接口规范](./contracts.md) 中的 `Advice`。

## `GET /api/reports`

用于报告中心列表。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码 |
| `pageSize` | 否 | 每页数量 |
| `inspectionId` | 否 | 巡检任务 ID |

响应 `data.items[]`：

```json
{
  "reportId": "report-20260616-0001",
  "inspectionId": "inspection-20260616-0001",
  "title": "电力设备巡检报告",
  "reportStatus": "ready",
  "createdAt": "2026-06-16T10:20:00+08:00",
  "format": "html",
  "url": "/reports/report-20260616-0001.html"
}
```

## `GET /api/reports/:id`

用于查看报告详情。

响应 `data`：

```json
{
  "reportId": "report-20260616-0001",
  "inspectionId": "inspection-20260616-0001",
  "title": "电力设备巡检报告",
  "summary": "本次巡检发现 1 项高风险故障。",
  "device": {
    "deviceId": "device-001",
    "deviceName": "2号线路绝缘子",
    "deviceType": "insulator",
    "location": "2号线路A相"
  },
  "faults": [],
  "alarms": [],
  "advices": [],
  "reportStatus": "ready",
  "exports": [],
  "createdAt": "2026-06-16T10:20:00+08:00"
}
```

## `GET /api/reports/:id/export`

用于获取或触发报告导出。

查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `format` | 否 | `html` 或 `pdf`，默认 `html` |

响应 `data` 使用 [数据契约与接口规范](./contracts.md) 中的 `ReportExport`。如果仍在生成，返回 `exportStatus: generating`；如果失败，返回 `exportStatus: failed` 并在统一错误响应中使用 `REPORT_EXPORT_FAILED`。
