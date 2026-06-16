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
