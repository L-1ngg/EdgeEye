# EdgeEye

EdgeEye is an inspection demo system with an Atlas/YOLO edge pipeline, a FastAPI backend, and a React dashboard frontend.

## Applications

```text
backend/  Python + FastAPI API service
web/      TypeScript + React + Vite frontend
docs/     contracts, member responsibilities, and integration notes
```

## Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Default backend URL:

```text
http://localhost:8000/api
```

Implemented backend endpoints:

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/dashboard`
- `POST /api/inspection/start`
- `POST /api/inspections/{id}/finish`
- `POST /api/inspections/{id}/fail`
- `GET /api/inspections`
- `GET /api/inspections/{id}/latest-result`
- `POST /api/detection/results`
- `GET /api/devices`
- `GET /api/faults`
- `GET /api/alarms`
- `GET /api/events`
- `PATCH /api/faults/{id}/status`
- `PATCH /api/alarms/{id}/status`
- `POST /api/advice/generate`
- `GET /api/faults/{id}/advice`
- `GET /api/reports`
- `GET /api/reports/{id}`
- `GET /api/reports/{id}/export`

Run backend tests:

```bash
cd backend
uv run pytest
```

## Frontend

```bash
cd web
bun install
bun run dev
```

Default frontend URL:

```text
http://localhost:5173
```

Build frontend:

```bash
cd web
bun run build
```

The frontend calls `/api` by default and falls back to typed mock data when the backend is unavailable. Set `VITE_API_BASE_URL` if the API runs on a different base URL.

## Contracts

The source of truth for cross-module fields and API behavior is:

- [docs/contracts.md](docs/contracts.md)
- [docs/openapi.yaml](docs/openapi.yaml)
- [docs/api-spec.md](docs/api-spec.md)
