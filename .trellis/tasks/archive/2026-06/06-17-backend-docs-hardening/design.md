# Design: Backend Hardening and Documentation

## Storage Hygiene

Runtime SQLite files under `backend/data/` must be ignored and should not be
tracked. If a database file is already tracked, remove it with `git rm --cached`
or `git rm` depending on whether the working file should remain locally. For
this task, generated runtime DB files are disposable and can be removed.

## Detection Validation

Keep validation at the API contract boundary using Pydantic models in
`backend/app/models/inspection.py`.

- `Performance.npuUsage` becomes `float | None`.
- `DetectionUploadRequest` performs cross-field validation:
  - each detection receives image dimensions if omitted;
  - bbox must have exactly four integers;
  - `0 <= x1 < x2 <= imageWidth`;
  - `0 <= y1 < y2 <= imageHeight`.

FastAPI's global validation handler already converts request validation errors
to `400 VALIDATION_ERROR`, so no route-level error code is needed.

## Static URL Convention

Mount two local static roots during `create_app()`:

- `/uploads` -> `EDGEEYE_UPLOADS_DIR`, default `uploads`
- `/reports` -> `EDGEEYE_REPORTS_DIR`, default `reports`

This does not change the JSON upload contract and does not add multipart
handling. It gives member 1 a clear integration path: generated raw/annotated
images can be placed under the backend uploads directory and referenced as
`/uploads/raw/...` and `/uploads/annotated/...`.

## Documentation

Update backend docs and code-specs with:

- upload/static directory convention;
- nullable NPU metric behavior;
- bbox validation rule;
- local DB hygiene;
- LLM provider/fallback configuration.

## Compatibility

Existing tests and payloads with numeric `npuUsage` remain valid. Frontend types
should allow `npuUsage: null` if the API contract changes.
