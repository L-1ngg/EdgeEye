# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend changes must preserve the documented API contract and include focused
pytest coverage for every new endpoint or behavior branch. Use `uv` for
dependency management.

---

## Forbidden Patterns

- Do not return raw dictionaries from route handlers when a Pydantic response model exists.
- Do not put database or business-rule logic directly in route modules.
- Do not introduce JSON fields or enum values that are absent from `docs/contracts.md` without updating the docs first.
- Do not commit `.venv/`, `__pycache__/`, `.pytest_cache/`, or other generated files.

---

## Required Patterns

- Wrap successful API responses in `ApiResponse[T]`.
- Keep public JSON fields in `camelCase`.
- Keep route modules grouped by domain and registered through `app/api/router.py`.
- Use service functions for demo data and future business logic.
- Keep request/response schemas in `backend/app/models/`; do not define
  Pydantic classes inside route functions.
- Keep test databases isolated with `reset_service_for_tests()` and temporary
  paths.

---

## Examples From This Codebase

Thin route plus service call:

```python
@router.post("/detection/results", response_model=ApiResponse[DetectionUploadResult])
def upload_detection_result(request: DetectionUploadRequest) -> ApiResponse[DetectionUploadResult]:
    return ApiResponse(data=get_service().upload_detection_result(request), timestamp=current_timestamp())
```

Isolated database fixture:

```python
@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    reset_service_for_tests(str(tmp_path / "edgeeye-test.db"))
```

Error-envelope assertion:

```python
assert conflict.status_code == 409
body = conflict.json()
assert body["success"] is False
assert body["error"]["code"] == "IDEMPOTENCY_CONFLICT"
```

---

## Testing Requirements

- Run backend tests with:

```bash
cd backend
uv run pytest
```

- New endpoints need at least one success-path test asserting HTTP status, `success`, and important `data` fields.
- Error branches need tests when validation, state transitions, idempotency, or upstream failures are implemented.

---

## Code Review Checklist

- Does the route response match `docs/contracts.md` and `docs/openapi.yaml`?
- Are route handlers thin enough to keep business logic testable?
- Are new dependencies reflected in `backend/pyproject.toml` and `backend/uv.lock`?
- Were generated files excluded by `.gitignore`?
- Does every new business error have a test that asserts the envelope code?
- Did the change avoid committing local runtime artifacts under `backend/data/`,
  `backend/uploads/`, or `backend/reports/`?
