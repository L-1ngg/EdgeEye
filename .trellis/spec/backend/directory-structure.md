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

- `backend/app/api/routes/health.py`
- `backend/app/api/routes/system.py`
- `backend/app/models/system.py`
- `backend/app/services/demo_data.py`
