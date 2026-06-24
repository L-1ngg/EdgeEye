# 故障中心展示故障证据图

## Goal

在故障中心右侧详情区域展示当前选中故障的最佳证据图，让用户可以从事件直接看到后端已保存的原图或标注图。

## Confirmed Facts

- 后端 `faults` 表保存了 `best_image_url` 和 `best_annotated_image_url`。
- `GET /api/events` 返回的 `EventItem.latestImageUrl` 优先使用 `best_annotated_image_url`，没有标注图时使用 `best_image_url`。
- 当前故障中心页面已经接收 `events`，但尚未展示 `latestImageUrl`。
- 本任务不需要新增接口字段，也不需要修改后端存储结构。

## Requirements

- 在 `FaultCenterPage` 的右侧选中事件详情中展示证据图。
- 证据图使用 `selectedEvent.latestImageUrl`，并带有当前最佳帧 ID。
- 如果没有图片 URL，展示清晰的空状态，不阻塞维修建议展示。
- 图片加载失败时要给出页面内提示，不出现破图占位。
- 样式需适配当前面板布局和移动端宽度，不新建嵌套卡片。

## Acceptance Criteria

- [x] 选中故障事件存在 `latestImageUrl` 时，右侧详情展示对应证据图。
- [x] 展示 `latestFrameId`，用户能知道图片对应哪一帧。
- [x] 图片加载失败或缺失时，显示中文空状态。
- [x] 不新增后端 API 或类型字段。
- [x] `cd web && bun run build` 通过。

## Notes

- 本任务为轻量前端展示优化，PRD-only。
