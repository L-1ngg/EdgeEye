# 自动刷新故障中心数据

## Goal

当实时巡检识别结果在后端自动落库后，前端故障中心、运行总览、资源页的故障/告警数据也能自动更新，不需要用户手动刷新页面。

## Confirmed Facts

- 后端检测结果进入 `POST /api/detection/results` 后会自动写入 `detection_results`、`faults` 和 `alarms`。
- 当前前端登录后只整体加载一次 `dashboard/events/faults/alarms`。
- 当前前端只有 `RealtimeSnapshot` 每 1 秒刷新。
- 本任务不需要新增后端接口，只需要复用现有 `getDashboard()`、`getEvents()`、`getFaults()`、`getAlarms()`、`getSystemOverview()`。

## Requirements

- 保持实时巡检 `snapshot` 每 1 秒刷新。
- 增加后台派生数据刷新，周期性拉取运行总览、系统状态、事件、故障、告警。
- 刷新后更新故障中心列表、资源页故障/告警、运行总览统计。
- 不清空用户已加载的维修建议缓存。
- 不直接从页面组件发起 `fetch`，继续通过 `web/src/api/client.ts`。
- 后台刷新失败时不覆盖已有可用数据，只标记相关数据源不可用。

## Acceptance Criteria

- [x] 实时巡检发现并落库新故障后，故障中心能在后台刷新周期内显示新事件。
- [x] 运行总览和系统资源页同步更新故障/告警数据。
- [x] 维修建议缓存 `adviceByFaultId` 不因后台刷新被重置。
- [x] 不新增后端 API。
- [x] `cd web && bun run build` 通过。

## Notes

- 本任务是轻量前端刷新行为优化，PRD-only。
