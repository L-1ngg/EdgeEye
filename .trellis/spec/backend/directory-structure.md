# Directory Structure

> How backend code is organized in this project.

---

## Overview

Backend code lives in `backend/` and uses FastAPI. Keep route handlers thin:
routes should validate HTTP input/output and call service functions; business
logic and later database access should not be embedded directly in route files.

---

## Directory Layout

```text
backend/
├── app/
│   ├── main.py              # FastAPI app creation and middleware wiring
│   ├── api/
│   │   ├── router.py        # top-level /api router registration
│   │   └── routes/          # route modules grouped by API domain
│   ├── core/                # settings and app-wide helpers
│   ├── models/              # Pydantic API models and shared enum literals
│   └── services/            # business/demo data services
├── tests/                   # pytest tests for API behavior
├── pyproject.toml
└── uv.lock
```

---

## Module Organization

- Add new HTTP endpoints under `backend/app/api/routes/<domain>.py`.
- Register route modules only in `backend/app/api/router.py`.
- Put API request/response schemas in `backend/app/models/`.
- Put implementation logic in `backend/app/services/` so it can later move from demo data to database-backed repositories without changing route signatures.
- Keep shared enum-like strings in `backend/app/models/common.py`.

---

## Naming Conventions

- Python files and directories use `snake_case`.
- JSON-facing Pydantic fields use `camelCase`, matching `docs/contracts.md`.
- Route function names should describe the endpoint action, for example `get_system_status`.
- Test files use `test_<domain>.py`.

---

## Examples

- Route modules:
  - `backend/app/api/routes/health.py` exposes `/api/health`.
  - `backend/app/api/routes/inspections.py` exposes inspection lifecycle and
    detection upload endpoints.
  - `backend/app/api/routes/assets.py` exposes devices, faults, alarms, events,
    and process-status updates.
- Router registration:
  - `backend/app/api/router.py` imports route modules and assigns path prefixes.
- Models:
  - `backend/app/models/inspection.py` owns inspection, detection, fault, alarm,
    advice, report, and pagination models.
  - `backend/app/models/responses.py` owns `ApiResponse[T]` and error payloads.
- Services:
  - `backend/app/services/inspection_service.py` owns database-backed business
    behavior.
  - `backend/app/services/storage.py` owns SQLite schema setup and compatibility
    column additions.
- Tests:
  - `backend/tests/test_member4_api.py` covers the end-to-end detection,
    advice, report, and dashboard flow.
  - `backend/tests/conftest.py` resets an isolated SQLite database for every
    test.

---

## Wrong vs Correct

### Wrong

```python
# backend/app/api/routes/reports.py
connection = sqlite3.connect("data/edgeeye.db")
rows = connection.execute("SELECT * FROM reports").fetchall()
```

### Correct

```python
@router.get("/reports", response_model=ApiResponse[PageResult[ReportListItem]])
def list_reports(page: int = 1, pageSize: int = 20) -> ApiResponse[PageResult[ReportListItem]]:
    return ApiResponse(
        data=get_service().list_reports(page=page, page_size=pageSize),
        timestamp=current_timestamp(),
    )
```

Route files own HTTP shape; `InspectionService` owns persistence and business
logic.
