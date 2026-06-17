# Frontend dashboard demo readiness

## Goal

Make the existing React/Vite frontend ready for a credible EdgeEye inspection
demo. The app should feel like an operational power-equipment inspection
dashboard, keep working with typed mock data when backend endpoints are not yet
available, and stay aligned with the documented API contracts.

## Confirmed Facts

- The frontend lives in `web/` and uses Bun, Vite, React 19, TypeScript, and
  global CSS in `web/src/styles/global.css`.
- Current app views are Dashboard, realtime inspection, fault center, and report
  center.
- `web/src/api/client.ts` is the API boundary. Page components should not call
  `fetch` directly.
- Shared API-facing types live in `web/src/types/contracts.ts` and should stay
  aligned with `docs/contracts.md` and `docs/api-spec.md`.
- `GET /api/dashboard` and `GET /api/system/status` exist in the FastAPI backend.
- Realtime snapshot, events, reports, and advice are currently mock-only on the
  frontend because backend routes are owned by another member and are not part
  of this task.
- The current frontend builds successfully with `bun run build`.
- Trellis frontend guidelines prefer dense, scannable operational UI and forbid
  marketing/landing-page composition.
- There is no existing frontend authentication implementation in `web/src`.

## Requirements

- Preserve the existing dashboard-shell direction: first screen is the working
  monitoring app, not a landing page.
- Improve frontend demo completeness across all current views:
  - Dashboard should make system health, unresolved work, and freshness obvious.
  - Realtime inspection should handle ready, stale, no-frame, processing, and
    failed states without broken layout.
  - Fault center should present backend-shaped aggregated events and repair
    advice clearly, without deriving alarm severity from raw detections.
  - Report center should make report generation/export states clear.
- Keep all data access in `web/src/api/`.
- Keep all API-facing types centralized in `web/src/types/contracts.ts`.
- Continue to use typed mock data as fallback for endpoints that are unavailable
  during integration.
- Keep the UI usable on mobile and desktop widths.
- Avoid introducing a component library or new package unless the need is clear
  and approved.
- Do not change backend implementation as part of this task.
- Keep missing backend endpoints represented through typed API client functions
  and typed mock fallback data so another member can later wire real FastAPI
  routes without changing page components.
- Add a minimal frontend-only administrator authentication gate suitable for
  the demo:
  - show a login screen before the dashboard shell;
  - accept a simple configured/demo administrator credential;
  - persist the logged-in demo session in browser storage;
  - provide a visible logout action;
  - do not claim this is production security.

## Acceptance Criteria

- [x] `web/src/api/client.ts` exposes frontend calls for the views being rendered
      and falls back intentionally when backend endpoints are unavailable.
- [x] `web/src/types/contracts.ts` covers every API-shaped payload used by the
      frontend pages without `any`.
- [x] Dashboard, realtime inspection, fault center, and report center each render
      useful states from the typed data available today.
- [x] App shows a minimal administrator login before the dashboard and supports
      logout.
- [x] Realtime page has explicit UI states for stale/no-frame/processing/failed
      snapshots.
- [x] Layout remains coherent at desktop and mobile widths with no obvious text
      overlap.
- [x] Frontend build passes with `bun run build`.

## Out of Scope

- Production authentication, authorization, password storage, token refresh,
  user/role management, and backend-enforced access control.
- Multi-camera management.
- Backend implementation, including new FastAPI routes, persistence, alarm
  generation, report generation, and LLM advice generation.
- A new frontend route library, global state library, or UI component kit unless
  explicitly approved later.
- Real report file generation.
- Model training, Atlas board deployment, or image upload implementation.

## Resolved Scope Decisions

- Backend development is owned by another member. This task must remain
  frontend-only and should not add missing FastAPI endpoints.
- External admin/dashboard templates may be used as visual and interaction
  references, but this task should not directly replace the current app with a
  full template or import a large template dependency stack.
- Authentication scope is limited to a frontend-only administrator gate for demo
  use. Backend authentication is out of scope.
- Demo administrator credential is `admin` / `edgeeye-admin`.
- If time is limited, prioritize the demo chain from Dashboard to realtime
  inspection to fault center; report center should remain clear and usable.

## Open Questions

- None.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
