# 前端演示数据残留审查

## Goal

Review the current frontend implementation for remaining demo/mock/sample data and record which items are still present versus which are only empty-state or unavailable-state UI.

## Requirements

- Inspect `web/src`, frontend build/config files, and frontend README for demo/mock/sample/fixture/fallback markers.
- Distinguish hardcoded demo behavior from legitimate empty, unavailable, or fallback UI states.
- Confirm whether the frontend still ships standalone mock business data such as fake devices, faults, alarms, reports, or inspections.
- Record actionable findings with file references so future cleanup can be planned without redoing the audit.
- Do not change runtime behavior in this task.

## Acceptance Criteria

- [x] Frontend source search covers demo/mock/sample/fixture/fallback terms.
- [x] Frontend data-source file search confirms whether `web/src/data`, mock, sample, or fixture sources exist.
- [x] Findings identify remaining hardcoded demo behavior.
- [x] Findings separate demo behavior from no-data/unavailable UI fallback.
- [x] `cd web && bun run build` passes after the audit.

## Findings Summary

- No standalone frontend mock-data source directory or file was found under `web/src`.
- The strongest remaining demo behavior is frontend-only local admin auth in `web/src/auth/session.ts` and `web/src/pages/LoginPage.tsx`.
- Realtime no-frame objects and app-wide empty data objects are unavailable/empty-state fallbacks, not fake business records.
- `web/README.md` still describes future "demo flows", which is documentation wording rather than runtime demo data.
- Status value `fallback` is part of advice status rendering and does not by itself indicate frontend mock data.

## Out of Scope

- Removing demo auth or replacing it with backend authentication.
- Rewriting empty-state fallback behavior.
- Backend seed/demo data audit.
- User-facing UI copy cleanup beyond identifying current frontend evidence.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
