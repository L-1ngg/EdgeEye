# Scaffold FastAPI backend and React frontend

## Goal

Create a runnable project skeleton for EdgeEye member 4 and member 5 work:

- `backend/`: Python + FastAPI API service foundation.
- `web/`: TypeScript + React + Vite frontend foundation.
- Shared project scripts and documentation so later feature work can build on a stable layout.

The skeleton should make the documented system shape concrete without trying to finish the full database, alarm, report, or LLM workflows in this task.

## Confirmed Facts

- Backend scope comes from `docs/04-backend-api.md`.
- Frontend scope comes from `docs/05-frontend-testing.md`.
- API contracts and field names are governed by `docs/contracts.md` and `docs/openapi.yaml`.
- The agreed technology choice is:
  - Backend language/framework: Python + FastAPI.
  - Frontend language/framework: TypeScript + React + Vite.
- The minimum integration path is:

```text
Atlas/mock detection result
  -> FastAPI API
  -> frontend dashboard/realtime/fault/report pages
```

## Requirements

- Add a backend app under `backend/` with:
  - FastAPI app factory or app instance.
  - Health and system status endpoints.
  - API router structure aligned with documented endpoint groups.
  - Pydantic models for common response envelopes and initial dashboard/system/demo data.
  - Basic tests for core endpoints.
  - Python dependency and run instructions.
- Add a frontend app under `web/` with:
  - Vite + React + TypeScript structure.
  - Routes or view-state navigation for Dashboard, realtime inspection, fault center, and report center.
  - API client boundary that can call the FastAPI service later.
  - Initial UI using typed mock data or graceful API fallback.
  - Basic build/type-check configuration.
- Add root-level developer documentation/scripts as needed so members can start both apps consistently.
- Keep implementation aligned with the existing documentation contracts:
  - JSON fields use `camelCase`.
  - Status/risk/advice enums use documented values.
  - Frontend must not derive alarm severity from raw detections; it should consume backend-shaped data.
- Keep this task focused on project skeleton. Full persistence, complete business rules, report generation, and real LLM calls are follow-up work.

## Acceptance Criteria

- [x] `backend/` contains a runnable FastAPI service.
- [x] `backend/` exposes at least `GET /api/health`, `GET /api/system/status`, and `GET /api/dashboard`.
- [x] Backend tests cover the initial endpoints.
- [x] `web/` contains a runnable React/Vite/TypeScript app.
- [x] Frontend includes visible skeleton views for Dashboard, realtime inspection, fault center, and report center.
- [x] Frontend can build successfully.
- [x] Root documentation explains how to run backend and frontend locally.
- [x] Existing docs remain valid; any necessary skeleton-specific notes are added without changing the agreed API contract.
- [ ] Work is committed after validation.

## Out of Scope

- Full database schema and migrations.
- Image upload/storage implementation.
- Complete detection result ingestion and idempotency behavior.
- Complete fault/alarm rule engine.
- Real LLM provider integration and API key management.
- Report PDF/Word generation.
- Production deployment packaging.

## Open Questions

- None blocking. Use a minimal, runnable skeleton first; defer full feature implementation to follow-up tasks.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
