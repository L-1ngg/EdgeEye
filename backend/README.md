# EdgeEye Backend

FastAPI service for EdgeEye member 4 work: API, SQLite persistence, dashboard data, system status, alarms, reports, and backend repair advice generation.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Default API base URL:

```text
http://localhost:8000/api
```

## Configuration

Environment variables use the `EDGEEYE_` prefix:

- `EDGEEYE_DATABASE_PATH`: SQLite database path. Defaults to `data/edgeeye.db`.
- `EDGEEYE_LLM_PROVIDER`: reserved provider selector. Defaults to `rule-template`.
- `EDGEEYE_LLM_API_KEY`: optional backend-only LLM API key. It is never returned to the frontend.
- `EDGEEYE_LLM_MODEL_NAME`: model name metadata for future provider calls.
- `EDGEEYE_LLM_TIMEOUT_SECONDS`: timeout for future provider calls.

When no provider is configured, `POST /api/advice/generate` saves and returns a complete rule-template fallback advice object.

## Member 4 Endpoints

- Inspections: `POST /api/inspection/start`, `POST /api/inspections/{id}/finish`, `POST /api/inspections/{id}/fail`, `GET /api/inspections`, `GET /api/inspections/{id}/latest-result`
- Detection upload: `POST /api/detection/results`
- Fault center: `GET /api/devices`, `GET /api/faults`, `GET /api/alarms`, `GET /api/events`, `PATCH /api/faults/{id}/status`, `PATCH /api/alarms/{id}/status`
- Advice: `POST /api/advice/generate`, `GET /api/faults/{id}/advice`
- Reports: `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/export`

## Test

```bash
uv run pytest
```
