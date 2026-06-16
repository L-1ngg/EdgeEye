# Error Handling

> How errors are handled in this project.

---

## Overview

Backend endpoints return a unified envelope for both success and error
responses. Business errors should raise `ApiException`; route handlers should
not build error dictionaries manually.

---

## Scenario: Unified API Error Envelope

### 1. Scope / Trigger

- Trigger: member 4 endpoints introduced validation, idempotency, state, and
  not-found errors.
- Applies to all FastAPI routes under `backend/app/api/routes/`.

### 2. Signatures

- Exception type:

```python
raise ApiException("NOT_FOUND", "fault not found", status_code=404)
```

- Handler registration:

```python
register_exception_handlers(app)
```

### 3. Contracts

- Success response:

```json
{"success": true, "data": {}, "message": "ok", "timestamp": "2026-06-16T10:00:00+08:00"}
```

- Error response:

```json
{"success": false, "error": {"code": "NOT_FOUND", "message": "fault not found", "details": null}, "timestamp": "2026-06-16T10:00:00+08:00"}
```

### 4. Validation & Error Matrix

- Pydantic/FastAPI request validation -> `400 VALIDATION_ERROR`.
- Missing resource -> `404 NOT_FOUND`.
- Invalid lifecycle transition -> `409 INVALID_STATE_TRANSITION`.
- Idempotency conflict -> `409 IDEMPOTENCY_CONFLICT`.
- Duplicate frame upload -> `409 DUPLICATE_UPLOAD`.
- Latest result missing -> `404 RESULT_NOT_READY`.
- Advice missing -> `404 ADVICE_NOT_READY`.

### 5. Good/Base/Bad Cases

- Good: service detects a business condition and raises `ApiException` with a
  documented error code.
- Base: request body shape errors are handled by the global validation handler.
- Bad: `raise HTTPException(...)` with an unwrapped `detail` payload from route
  code.

### 6. Tests Required

- Assert `success is false` and `error.code` for every implemented non-2xx
  branch.
- Idempotency conflict tests must assert HTTP 409 and `IDEMPOTENCY_CONFLICT`.
- Endpoint success tests must assert `success is true` and important `data`
  fields.

### 7. Wrong vs Correct

#### Wrong

```python
raise HTTPException(status_code=404, detail="fault not found")
```

#### Correct

```python
raise ApiException("NOT_FOUND", "fault not found", status_code=404)
```

---

## Error Types

- `ApiException`: business/API error with `code`, `message`, `status_code`, and
  optional `details`.
- `RequestValidationError`: converted globally to `VALIDATION_ERROR`.

---

## Error Handling Patterns

- Service layer raises errors.
- Route layer returns `ApiResponse[T]` for successful calls.
- `main.create_app()` registers global exception handlers once.

---

## API Error Responses

Use the codes documented in `docs/contracts.md`. If a new code is needed, update
`docs/contracts.md`, `docs/openapi.yaml`, and tests in the same change.

---

## Common Mistakes

- Do not return `{"success": false}` manually from routes.
- Do not leak stack traces, SQL errors, or LLM provider secrets through
  `details`.
