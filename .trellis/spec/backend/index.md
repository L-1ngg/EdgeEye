# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | Active |
| [Error Handling](./error-handling.md) | Error types, handling strategies | Active |
| [Detection Upload Adapters](./detection-upload-adapters.md) | Edge/model adapter payload contract and ONNX debug bridge rules | Active |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | To fill |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

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
- Read `detection-upload-adapters.md` before changing edge/model adapter output or the detection upload payload.
- Read `quality-guidelines.md` before adding or changing endpoints.
- Keep API response fields aligned with `docs/contracts.md` and `docs/openapi.yaml`.
