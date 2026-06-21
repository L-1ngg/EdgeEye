# 接口、数据流与交付边界

## 总体数据流

```text
摄像头
   ↓
成员1：Atlas 采集与推理
   ↓
成员2：目标检测模型结果
   ↓
成员3：故障规则和维修建议内容
   ↓
成员4：后端保存、告警、报告、大模型维修建议
   ↓
成员5：前端展示和系统测试
```

## 借鉴来源

目标检测与 Atlas 部署可参考 `atlas-insulator-detection` 的拆分方式：

参考仓库：<https://gitee.com/jerry12345555555/atlas-insulator-detection>

- 训练层：`dataset.yaml`、YOLO 标签、`train.py`、`best.pt`；
- 转换层：`best.pt -> best.onnx -> atc -> best.om`；
- 部署层：板端 ACL 加载 OM、单例推理、NMS、可视化输出；
- 联调层：本机中转后端 + 开发板推理服务 + 前端上传展示。

EdgeEye 只借鉴这些流程和工程边界，不直接继承对方的后端数据契约。我们自己的主接口仍以 `docs/contracts.md` 和 `docs/openapi.yaml` 为准。

## 模块交付关系

| 来源 | 接收方 | 交付内容 |
| --- | --- | --- |
| 成员2 | 成员1 | ONNX 模型、类别文件、预处理和后处理参数 |
| 成员4 | 成员1 | 后端上传接口和字段定义 |
| 成员1 | 成员4 | 检测结果、图片、性能数据 |
| 成员2 | 成员3 | 设备类别、故障类别、置信度 |
| 成员3 | 成员4 | 规则文件、提示词模板、维修建议输出格式 |
| 成员4 | 成员5 | 设备、巡检、故障、告警、报告和建议接口 |
| 成员5 | 全组 | 联调问题、演示流程、缺陷记录 |

## 职责边界

| 功能 | 成员1 | 成员2 | 成员3 | 成员4 | 成员5 |
| --- | --- | --- | --- | --- | --- |
| 摄像头接入 | 主负责 |  |  |  | 测试 |
| Atlas 部署 | 主负责 | 协助 | 协助 |  |  |
| 设备识别 | 部署 | 主负责 |  | 保存结果 | 展示 |
| 故障检测 | 部署 | 主负责 | 制定风险规则 | 保存和告警 | 展示 |
| 环境异常检测 | 部署 | 主负责 | 制定告警规则 | 保存和告警 | 展示 |
| 大模型维修建议规则 |  | 提供故障类别 | 主负责 | 协助 | 展示 |
| 大模型后端调用 |  |  | 提供提示词 | 主负责 | 展示 |
| 数据库和 API | 上传数据 |  |  | 主负责 | 调用接口 |
| 巡检报告 |  |  | 提供建议内容 | 主负责 | 展示与导出 |
| 系统测试 | 边缘端测试 | 模型测试 | 专项算法测试 | 接口测试 | 主负责 |

## Atlas 上传检测结果格式

详细字段、枚举和 API 响应包裹格式见 [数据契约与接口规范](./contracts.md)。这里保留 Atlas 上传到后端的最常用结果结构。`Fault` 和 `Alarm` 由后端根据规则生成，不由 Atlas 上传。

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
    },
    {
      "category": "smoke",
      "deviceType": null,
      "faultType": "smoke",
      "confidence": 0.88,
      "bbox": [420, 60, 600, 260]
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

前端查询最新巡检结果时，`GET /api/inspections/:id/latest-result` 可以返回后端生成的 `faults` 字段；这不是上传字段。
边缘端必须执行关键帧选择和幂等上传；后端必须按 `eventKey` 聚合同一故障事件。

## 页面与接口边界

| 前端页面 | 必要接口 | 页面职责 |
| --- | --- | --- |
| Dashboard | `GET /api/dashboard`、`GET /api/system/status` | 展示统计、摄像头状态、Atlas 状态、模型状态和后端状态 |
| 实时巡检 | `GET /api/camera/stream.mjpg` + `GET /api/inspections/:id/latest-result` | MJPEG 展示实时画面；latest-result 展示检测框、设备识别、实时故障和性能数据 |
| 故障中心 | `GET /api/events`、`GET /api/faults`、`GET /api/alarms`、`POST /api/advice/generate`、`GET /api/faults/:id/advice` | 展示聚合事件、故障、告警、处理状态和大模型维修建议 |
| 报告中心 | `GET /api/reports`、`GET /api/reports/:id`、`GET /api/reports/:id/export` | 展示巡检报告并提供导出入口 |

## 最小联调链路

第一周必须完成：

```text
摄像头读取
   ↓
Atlas 运行模型
   ↓
后端接收结果
   ↓
数据库保存
   ↓
前端展示结果
```

最小可用验收：

- 摄像头能够读取；
- Atlas 能够运行一个模型；
- 后端能够按 [数据契约与接口规范](./contracts.md) 接收检测结果；
- 前端能够展示一条实时或模拟检测结果，包括设备结果、故障结果和大模型维修建议。

## 联调准入

第 6-7 天进入全组联调前，必须满足 [工程规范与联调标准](./engineering-standards.md) 中的联调准入清单。任何模块临时改字段、改枚举、改接口路径，都必须同步更新 `docs/contracts.md`。

## 交付物总览

| 成员 | 交付物 |
| --- | --- |
| 成员1 | `edge-app/`、`camera/`、`model-deploy/`、`config/`、部署说明、性能测试报告 |
| 成员2 | `dataset/`、`labels/`、`training/`、`best.onnx`、`classes.json`、模型评估报告、标注规范 |
| 成员3 | `rules/fault-rules.json`、`rules/alarm-rules.json`、`prompt-template/`、大模型维修建议测试样例、规则和建议内容测试报告 |
| 成员4 | `server/`、`database/`、`api-docs/`、`report-template/`、`docker-compose.yml`、大模型维修建议接口 |
| 成员5 | `web/`、`test-cases/`、`demo-data/`、`screenshots/`、`demo-video/`、用户手册、答辩 PPT |
