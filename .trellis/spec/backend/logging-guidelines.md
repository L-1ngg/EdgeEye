# Backend Logging Guidelines

> Logging and diagnostic boundaries for the FastAPI backend.

---

## Current State

The current backend does not define a project-level structured logging
pipeline. FastAPI/Uvicorn provide server access logs when the service is run
with `uv run uvicorn app.main:app --reload`; application code currently relies
on explicit API responses and tests rather than ad hoc runtime logs.

Do not introduce casual `print()` debugging, request-body dumps, or provider
payload logs. If a future task needs application logging, add it deliberately in
`backend/app/core/` and document the format here in the same change.

---

## Diagnostic Boundaries

- Business/API failures are observable through the unified error envelope from
  `backend/app/core/errors.py`.
- LLM provider failures are handled inside
  `backend/app/services/inspection_service.py` by saving rule-template fallback
  advice; provider internals are not surfaced to clients.
- Static file paths for `/uploads` and `/reports` come from
  `backend/app/main.py` and settings, not from request logs.
- Tests assert behavior through HTTP responses, database-backed state, and
  generated report files rather than matching log lines.

---

## What To Log If Logging Is Added

Use Python's standard `logging` module or a reviewed project wrapper. Keep logs
operational and low-cardinality:

- App startup configuration that is not sensitive: app version, enabled static
  roots, database path basename if needed.
- Inspection lifecycle transitions: started, completed, failed.
- Detection upload outcomes: accepted, duplicate, idempotency conflict,
  duplicate frame.
- Report export failures that need operator attention.
- LLM provider call outcome at status level only: success, retry exhausted,
  fallback used.

Keep route handlers thin. Prefer logging in service functions where the
business outcome is known.

---

## What Not To Log

- `EDGEEYE_LLM_API_KEY` or any credential-bearing header.
- Full detection payloads, image URLs with private tokens, or uploaded file
  bytes.
- Full LLM prompt or provider response bodies.
- SQLite exception details that may expose local paths or implementation
  internals.
- Stack traces in API responses.

---

## Wrong vs Correct

### Wrong

```python
print(request.model_dump())
raise HTTPException(status_code=500, detail=str(exc))
```

This leaks request data and bypasses the response contract.

### Correct

```python
raise ApiException(
    "IDEMPOTENCY_CONFLICT",
    "same idempotency key was used for different content",
    status_code=409,
)
```

The client gets a documented error code, and tests can assert the behavior
without depending on logs.

---

## Common Mistakes

- Do not add `print()` statements while debugging and forget to remove them.
- Do not log secrets from `Settings` or provider calls.
- Do not depend on log output for test assertions until a real logging contract
  exists.
- Do not invent a new logging dependency without updating `backend/pyproject.toml`,
  `backend/uv.lock`, and this guideline.
