# EdgeEye Backend

FastAPI service for EdgeEye member 4 work: API, dashboard data, system status, and later persistence, alarms, reports, and LLM repair advice.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Default API base URL:

```text
http://localhost:8000/api
```

## Test

```bash
uv run pytest
```
