# Implementation Plan

## Order

1. Read relevant Trellis backend/frontend specs before editing application code.
2. Extend backend settings with database and LLM-related configuration.
3. Add contract models for member 4 payloads.
4. Add SQLite storage and deterministic seed/reset support.
5. Add inspection service business logic for upload idempotency, fault/alarm
   generation, advice fallback, reports, dashboard, and system summaries.
6. Add FastAPI routes and register them in `app/api/router.py`.
7. Update existing dashboard/system routes to call the new service.
8. Add backend tests for the full member 4 workflow and idempotency behavior.
9. Wire frontend API client to realtime, events, advice, and reports endpoints
   with existing mock fallback retained.
10. Update README/backend docs for new endpoints and environment variables.
11. Run validation:
    - `uv run pytest` from `backend/`
    - frontend type-check/build command from `web/package.json`
    - `git status --short`
12. Commit and push to `origin/main`.

## Risky Files

- `backend/app/api/router.py`
- `backend/app/services/*`
- `backend/app/models/*`
- `web/src/api/client.ts`
- `web/src/types/contracts.ts`

## Review Gates

- The OpenAPI-documented endpoint paths must exist.
- Idempotent duplicate uploads must not create duplicate faults/alarms/advice.
- Fallback advice must still return a complete `Advice` object.
- Report generation must use `reportStatus`, not `inspectionStatus`.
- Frontend fallback behavior must remain intact.
