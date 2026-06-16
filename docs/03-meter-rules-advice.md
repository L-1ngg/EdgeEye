# 成员3：仪表读数、故障规则与智能建议设计

## 开发目标

负责目标检测之后的专项识别和业务判断，包括仪表读数、阈值判断、故障规则、风险等级和智能建议内容设计。

成员3解决的问题：

```text
仪表显示多少、是否超限、故障严重程度如何、应该给出什么处理建议。
```

## 职责范围

主负责：

- 仪表读数识别；
- 仪表数值格式校验；
- 仪表正常、预警和异常阈值；
- 故障告警规则；
- 风险等级定义；
- 智能建议提示词；
- 智能建议输入输出格式；
- 规则文件版本和阈值版本；
- 故障事件聚合规则；
- 大模型失败时的规则模板降级建议；
- 建议内容质量测试。

不负责：

- 通用目标检测模型训练；
- Atlas 环境部署；
- 后端接口开发；
- 大模型 API Key 管理；
- 前端页面实现。

## 仪表识别范围

两周内建议只做一种固定型号的数字仪表。

推荐流程：

```text
成员2检测仪表位置
   ↓
裁剪仪表区域
   ↓
透视校正
   ↓
灰度化和二值化
   ↓
OCR 识别
   ↓
数字格式校验
   ↓
数值范围判断
```

只有题目明确要求时再做指针仪表：

```text
仪表定位
   ↓
表盘裁剪
   ↓
圆心检测
   ↓
指针提取
   ↓
指针角度计算
   ↓
映射为实际数值
```

## 输入

- 成员2输出的仪表检测框；
- 仪表裁剪图；
- 仪表类型；
- 设备类型；
- 故障检测结果；
- 业务阈值要求。

## 输出

仪表识别输出示例：

```json
{
  "meterId": "device-001",
  "meterType": "voltage_meter",
  "value": 235.6,
  "unit": "V",
  "readingStatus": "normal",
  "confidence": 0.89,
  "rawText": "235.6",
  "imageUrl": "/uploads/meter/inspection-20260616-0001/frame-000001-meter-001.jpg"
}
```

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

成员3交付的是规则和建议内容结构，不直接生成带 `faultId` 的持久化 `Fault`。后端根据检测结果、仪表读数和规则文件生成 `Fault`、`Alarm`。

智能建议输出示例：

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
    "操作前确认设备状态",
    "维修建议需人工审核"
  ]
}
```

后端保存后会补充 `adviceId`、`faultId`、`modelName` 和 `createdAt`，完整结构见 [数据契约与接口规范](./contracts.md) 中的 `Advice`。

## 任务清单

### 仪表读数识别

- 收集固定数字仪表测试图片；
- 确认仪表单位和读数格式；
- 完成仪表区域裁剪输入适配；
- 实现图像预处理；
- 跑通 OCR 识别；
- 过滤非数字字符；
- 校验小数点、负号和单位；
- 输出统一 JSON 结果；
- 字段名和枚举值遵守 [数据契约与接口规范](./contracts.md)；
- 准备成功、失败和低置信度样例。

### 阈值与状态判断

以电压表为例：

```text
电压 < 220V：低压预警
220V <= 电压 <= 240V：正常
电压 > 240V：过压预警
```

需要定义：

- 正常范围；
- 预警范围；
- 故障范围；
- 异常值处理；
- OCR 失败处理；
- 低置信度处理。

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

### 智能建议设计

成员3负责设计业务内容，成员4负责在后端调用大模型。

需要完成：

- 整理故障类型；
- 整理可能原因；
- 整理巡检建议；
- 整理维修建议；
- 整理安全提示；
- 设计提示词模板；
- 设计输入 JSON；
- 设计输出 JSON；
- 设计安全约束；
- 设计规则模板降级输出；
- 定义 `adviceStatus` 从 `generating` 到 `ready/fallback/failed` 的判断；
- 测试输出是否合理。

智能建议输入示例：

```json
{
  "deviceType": "insulator",
  "deviceName": "2号线路绝缘子",
  "faultType": "surface_damage",
  "confidence": 0.91,
  "riskLevel": "high",
  "location": "2号线路A相"
}
```

### 规则版本要求

`fault-rules.json`、`alarm-rules.json` 和 `meter-thresholds.json` 必须包含 `version` 和 `updatedAt`。后端保存 `Fault`、`Alarm` 和 `Advice` 时应记录使用的规则版本，便于复盘同一检测结果为何生成某个风险等级。

### 事件聚合建议

- 同一 `inspectionId + deviceId + faultType` 默认视为同一事件；
- 连续命中时更新 `lastSeenAt` 和 `occurrenceCount`；
- 超过规则定义的恢复窗口未再命中时，可生成 `fault_resolved` 事件；
- 仪表读数从 `normal` 变为 `warning/critical` 时上传 `meter_status_changed`；
- OCR 失败连续出现时才建议生成 `meter_read_failed`，避免单帧误识别导致告警。

## 建议目录

```text
meter-reader/
rules/
prompt-template/
test-samples/
reports/
```

## 交付物

- 仪表识别模块；
- `fault-rules.json`；
- `alarm-rules.json`；
- `meter-thresholds.json`；
- 智能建议提示词模板；
- 智能建议输入输出格式说明；
- 智能建议测试样例；
- 仪表识别测试报告。

## 验收标准

- 能对固定数字仪表图片输出读数；
- 能判断仪表读数正常、预警或异常；
- 能根据目标检测结果生成风险等级；
- 能输出告警触发结果；
- 能提供给成员4可直接调用的规则文件和提示词，格式遵守 [工程规范与联调标准](./engineering-standards.md)；
- 智能建议输出结构稳定，且包含原因、风险、巡检步骤、维修建议和安全提示。
