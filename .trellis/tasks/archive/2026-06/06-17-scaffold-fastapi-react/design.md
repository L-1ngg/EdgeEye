# Scaffold FastAPI Backend and React Frontend - Design

## Architecture

Use a split application layout:

```text
backend/
  app/
    main.py
    api/
    core/
    models/
    services/
  tests/
  pyproject.toml

web/
  src/
    api/
    components/
    data/
    pages/
    styles/
    types/
  package.json
  vite.config.ts
```

The backend owns API response shapes, status data, dashboard data, and later persistence/business logic. The frontend owns visual composition, page state rendering, and API consumption.

## Backend Boundary

The first skeleton should expose stable, low-risk endpoints:

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/dashboard`

The code should already be organized for later endpoint groups:

- inspections
- detection results
- devices
- faults
- alarms
- events
- advice
- reports

For this task, those groups can remain directory/router placeholders if not needed for the initial runnable app.

## Frontend Boundary

The frontend should be an operational dashboard shell, not a landing page. It should include:

- Dashboard view.
- Realtime inspection view.
- Fault center view.
- Report center view.

The initial UI may use local mock data or API fallback, but all data should be typed with project-specific TypeScript types that mirror the documented contracts.

## Contracts

Use `camelCase` for JSON-facing fields and TypeScript API types. Keep enum strings compatible with `docs/contracts.md`.

The skeleton should avoid creating a competing contract source. `docs/contracts.md` and `docs/openapi.yaml` remain authoritative.

## Data Flow

Initial development flow:

```text
FastAPI mock/demo service data
  -> JSON API response
  -> frontend API client
  -> page-level typed data
  -> visual cards/tables/status panels
```

Later feature tasks can replace demo service data with database-backed repositories without changing the frontend page boundary.

## Tooling

Backend:

- Python 3.11+.
- FastAPI.
- Uvicorn.
- Pydantic.
- pytest + HTTPX/TestClient.

Frontend:

- TypeScript.
- React.
- Vite.
- Bun as the package manager when available.

## Trade-offs

- SQLite/database setup is intentionally deferred. This keeps the skeleton small and avoids locking table design before the API/service boundary is proven.
- React Router can be deferred if a simple tabbed shell is enough for the first skeleton. A route-based app can be added later without changing core page components.
- Styling should be restrained and operational, matching a monitoring/dashboard product rather than a marketing page.

## Rollback

The task adds new top-level app directories and config files. Rollback is straightforward by reverting the task commit if the selected skeleton needs to be replaced.
