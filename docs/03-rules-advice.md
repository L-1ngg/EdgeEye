# 成员3：故障规则与大模型维修建议设计

## 开发目标

负责目标检测之后的业务判断和维修建议内容设计，包括故障规则、风险等级、告警触发条件、提示词模板和大模型维修建议输出格式。

成员3解决的问题：

```text
检测到的故障严重程度如何、是否需要告警、应该给出什么维修建议。
```

## 职责范围

主负责：

- 故障类型和风险等级定义；
- 故障告警规则；
- 处理优先级定义；
- 事件聚合规则；
- 大模型维修建议提示词；
- 大模型维修建议输入输出格式；
- 规则文件版本管理；
- 大模型失败时的规则模板降级建议；
- 建议内容质量测试。

不负责：

- 通用目标检测模型训练；
- Atlas 环境部署；
- 仪表读数识别；
- 仪表数值是否超限；
- 后端接口开发；
- 大模型 API Key 管理；
- 前端页面实现。

## 仪表相关边界

当前版本不做仪表识别：

- 不做数字仪表 OCR；
- 不做指针仪表识别；
- 不输出仪表读数、单位或读数状态；
- 不根据仪表读数生成超限告警。

如果成员2将仪表作为普通设备目标检测，结果只按 `Detection` 中的 `deviceType: "meter"` 展示，不进入读数和阈值判断链路。

## 输入

- 成员2输出的设备类别、故障类别、置信度和检测框；
- 设备类型；
- 设备名称和位置；
- 巡检任务信息；
- 业务风险要求；
- 后端已有故障和告警状态。

## 输出

故障规则输出示例：

```json
{
  "deviceType": "insulator",
  "faultType": "surface_damage",
  "minConfidence": 0.8,
  "riskLevel": "high",
  "alarmRequired": true,
  "alarmLevel": "warning",
  "priority": "P1"
}
```

成员3交付的是规则和维修建议内容结构，不直接生成带 `faultId` 的持久化 `Fault`。后端根据检测结果和规则文件生成 `Fault`、`Alarm`，再调用大模型生成 `Advice`。

大模型维修建议输出示例：

```json
{
  "possibleCauses": [
    "机械冲击",
    "长期老化"
  ],
  "riskAnalysis": "可能降低绝缘性能",
  "inspectionSteps": [
    "检查破损范围",
    "检查是否存在放电痕迹"
  ],
  "maintenanceSuggestions": [
    "安排专业人员复检",
    "必要时更换绝缘子"
  ],
  "safetyNotes": [
    "操作前确认设备停电或处于安全隔离状态",
    "维修建议必须由现场专业人员复核后执行"
  ]
}
```

后端保存后会补充 `adviceId`、`faultId`、`modelName`、`adviceStatus` 和 `createdAt`，完整结构见 [数据契约与接口规范](./contracts.md) 中的 `Advice`。

## 任务清单

### 故障与告警规则

需要定义：

- 故障类型；
- 触发条件；
- 置信度阈值；
- 风险等级；
- 告警等级；
- 处理优先级；
- 是否需要人工复核；
- `eventKey` 生成规则；
- 同一事件持续和恢复的判定条件。

规则示例：

```text
绝缘子破损 + 置信度 > 0.8
→ 风险等级：高
→ 告警等级：预警
→ 处理优先级：P1
```

### 大模型维修建议设计

成员3负责设计业务内容，成员4负责在后端调用大模型。

需要完成：

- 整理故障类型；
- 整理可能原因；
- 整理复检步骤；
- 整理维修建议；
- 整理安全提示；
- 设计提示词模板；
- 设计输入 JSON；
- 设计输出 JSON；
- 设计安全约束；
- 设计规则模板降级输出；
- 定义 `adviceStatus` 从 `generating` 到 `ready/fallback/failed` 的判断；
- 测试输出是否合理。

大模型维修建议输入示例：

```json
{
  "deviceType": "insulator",
  "deviceName": "2号线路绝缘子",
  "faultType": "surface_damage",
  "confidence": 0.91,
  "riskLevel": "high",
  "location": "2号线路A相",
  "bestImageUrl": "/uploads/annotated/inspection-20260616-0001/frame-000021.jpg"
}
```

### 规则版本要求

`fault-rules.json` 和 `alarm-rules.json` 必须包含 `version` 和 `updatedAt`。后端保存 `Fault`、`Alarm` 和 `Advice` 时应记录使用的规则版本，便于复盘同一检测结果为何生成某个风险等级。

### 事件聚合建议

- 同一 `inspectionId + deviceId + faultType` 默认视为同一事件；
- 连续命中时更新 `lastSeenAt` 和 `occurrenceCount`；
- 超过规则定义的恢复窗口未再命中时，可生成 `fault_resolved` 事件；
- 同一事件只保留最佳证据帧，优先选择风险等级最高、置信度最高的帧；
- 大模型维修建议默认按故障事件生成，不按每一帧重复生成。

## 建议目录

```text
rules/
prompt-template/
test-samples/
reports/
```

## 交付物

- `fault-rules.json`；
- `alarm-rules.json`；
- 大模型维修建议提示词模板；
- 大模型维修建议输入输出格式说明；
- 大模型维修建议测试样例；
- 规则模板降级建议样例；
- 规则和建议内容测试报告。

## 验收标准

- 能根据目标检测结果生成风险等级；
- 能输出告警触发结果；
- 能提供给成员4可直接调用的规则文件和提示词，格式遵守 [工程规范与联调标准](./engineering-standards.md)；
- 大模型维修建议输出结构稳定，且包含原因、风险、复检步骤、维修建议和安全提示；
- 大模型失败时能提供可展示的规则模板降级建议。
