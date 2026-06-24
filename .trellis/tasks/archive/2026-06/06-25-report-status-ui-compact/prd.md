# 报告中心状态列 UI 优化

## Goal

Improve the report center table status UI so the report status indicator is compact and visually balanced instead of stretching across the whole status column.

## Requirements

- Scope is limited to the frontend report center table UI.
- Keep the shared `StatusPill` label mapping and status semantics.
- Make the status pill in the report table size to its content and align cleanly within the status column.
- Preserve existing report export behavior and API data flow.

## Acceptance Criteria

- [x] Report table status cells no longer render as a long green bar for `ready` reports.
- [x] Status pills remain readable and consistent with the existing dashboard style.
- [x] Report table layout remains stable at desktop and mobile responsive widths.
- [x] `cd web && bun run build` passes.

## Out of Scope

- Backend report data changes.
- Authentication, report export, or API client behavior changes.
- Global redesign of all status pills outside the report table.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
