# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains EdgeEye backend conventions discovered from the
FastAPI service under `backend/`. Follow these files before changing routes,
Pydantic models, settings, persistence, report generation, or tests.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Active |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | Active |
| [Error Handling](./error-handling.md) | Error types, handling strategies | Active |
| [Detection Upload Adapters](./detection-upload-adapters.md) | Edge/model adapter payload contract and ONNX debug bridge rules | Active |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Active |
| [Logging Guidelines](./logging-guidelines.md) | Logging and sensitive-data boundaries | Active |

---

**Language**: All documentation should be written in **English**.

## Current Stack

- Runtime: Python 3.11+.
- Web framework: FastAPI.
- Validation and response schemas: Pydantic.
- Package/dependency workflow: `uv`.
- Tests: `pytest` with FastAPI `TestClient`.

## Pre-Development Checklist

- Read `directory-structure.md` before adding backend modules.
- Read `database-guidelines.md`, `error-handling.md`, and `quality-guidelines.md` before adding or changing endpoints.
- Read `logging-guidelines.md` before adding operational diagnostics, provider calls, or exception handling.
- Read `detection-upload-adapters.md` before changing edge/model adapter output or the detection upload payload.
- Keep API response fields aligned with `docs/contracts.md` and `docs/openapi.yaml`.
- Run `cd backend && uv run pytest` before committing backend behavior changes.
