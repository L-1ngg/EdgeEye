# Scaffold FastAPI Backend and React Frontend - Implementation Plan

## Checklist

1. [x] Inspect current repo for package manager and existing app files.
2. [x] Create backend skeleton:
   - `backend/pyproject.toml`
   - FastAPI app entrypoint.
   - API router modules.
   - Pydantic schemas.
   - Demo service data.
   - pytest coverage for initial endpoints.
3. [x] Create frontend skeleton:
   - `web/package.json`
   - Vite/React/TypeScript config.
   - typed API client and shared types.
   - Dashboard/realtime/fault/report views.
   - responsive operational styling.
4. [x] Add root documentation/scripts if useful.
5. [x] Run validation:
   - backend tests.
   - frontend type-check/build.
   - formatting or diff checks available in the repo.
6. [ ] Update task state and commit.

## Validation Commands

Preferred commands:

```bash
cd backend && uv sync && uv run pytest
cd web && bun install && bun run build
git diff --check
```

If `uv` or `bun` is unavailable, use the closest available local equivalent and report the substitution.

## Risk Points

- Dependency installation can fail if the environment lacks network access.
- Frontend package lock creation should use Bun if possible.
- Do not add full database or LLM implementation in this task.
- Do not alter the already agreed `docs/openapi.yaml` unless the skeleton exposes a deliberate contract correction.

## Review Gate

Before starting implementation:

- PRD, design, and implementation plan exist.
- Scope is skeleton-only and does not include full persistence/rule/LLM/report behavior.
