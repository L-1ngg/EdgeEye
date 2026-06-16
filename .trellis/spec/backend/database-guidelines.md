# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The backend uses Python's standard `sqlite3` module for the current member 4
demo service. Do not add an ORM unless a future task explicitly plans
migrations and dependency changes.

The default database path is configured by `EDGEEYE_DATABASE_PATH` and defaults
to `data/edgeeye.db` when running from `backend/`.

---

## Scenario: Member 4 SQLite Store

### 1. Scope / Trigger

- Trigger: member 4 backend work added persistent storage for inspections,
  detection results, faults, alarms, advice, and reports.
- Applies when modifying `backend/app/services/storage.py` or
  `backend/app/services/inspection_service.py`.

### 2. Signatures

- Store constructor: `SQLiteStore(database_path: str)`.
- Service accessor: `get_service() -> InspectionService`.
- Test reset helper: `reset_service_for_tests(database_path: str)`.
- Tables:
  - `devices(device_id PRIMARY KEY, device_type, status, created_at, updated_at)`
  - `inspections(inspection_id PRIMARY KEY, device_id, status, started_at, ended_at)`
  - `detection_results(result_id PRIMARY KEY, idempotency_key UNIQUE, payload_hash, inspection_id, frame_id, detections_json, performance_json)`
  - `faults(fault_id PRIMARY KEY, event_key UNIQUE, process_status, occurrence_count)`
  - `alarms(alarm_id PRIMARY KEY, dedup_key UNIQUE, process_status, suppressed_count)`
  - `advice(advice_id PRIMARY KEY, fault_id UNIQUE, advice_status)`
  - `reports(report_id PRIMARY KEY, inspection_id, report_status, format, version)`

### 3. Contracts

- JSON-facing fields stay `camelCase` in Pydantic models.
- SQLite columns use `snake_case`.
- Nested display payloads are stored as JSON text:
  - `detections_json`
  - `performance_json`
  - `sample_window_json`
  - `exports_json`
- Environment keys:
  - `EDGEEYE_DATABASE_PATH`: optional SQLite file path.
  - `EDGEEYE_LLM_API_KEY`: optional backend-only secret; never write it to DB responses.

### 4. Validation & Error Matrix

- Duplicate `idempotency_key` with same `payload_hash` -> return original result with `duplicate: true`.
- Duplicate `idempotency_key` with different `payload_hash` -> `409 IDEMPOTENCY_CONFLICT`.
- Upload to completed/failed inspection -> `409 INSPECTION_NOT_RUNNING`.
- Missing inspection/report/fault/alarm -> `404 NOT_FOUND`.
- Same `(inspection_id, frame_id)` with a different upload key -> `409 DUPLICATE_UPLOAD`.

### 5. Good/Base/Bad Cases

- Good: route validates request, service hashes canonical payload, DB persists once, service returns Pydantic response.
- Base: new Atlas upload can create a running inspection when the inspection ID does not exist yet.
- Bad: route handler opens SQLite directly or writes raw dict responses.

### 6. Tests Required

- Start inspection, upload detection, assert `faultsCreated` and `alarmsCreated`.
- Repeat identical upload, assert `duplicate: true` and no new fault/alarm counters.
- Repeat same key with changed payload, assert `IDEMPOTENCY_CONFLICT`.
- Finish inspection, assert report list/detail/export endpoints return ready data.

### 7. Wrong vs Correct

#### Wrong

```python
@router.post("/detection/results")
def upload(payload: dict):
    sqlite3.connect("edgeeye.db").execute("INSERT ...")
    return {"resultId": "..."}
```

#### Correct

```python
@router.post("/detection/results", response_model=ApiResponse[DetectionUploadResult])
def upload_detection_result(request: DetectionUploadRequest) -> ApiResponse[DetectionUploadResult]:
    return ApiResponse(data=get_service().upload_detection_result(request), timestamp=current_timestamp())
```

---

## Query Patterns

- Open a short-lived connection per service operation through `SQLiteStore.connect()`.
- Keep transactions inside service methods using `with self.store.connect() as connection:`.
- Route modules must not run SQL.
- Use parameterized SQL for user-provided values.

---

## Migrations

There is no migration framework yet. Schema is created by `SCHEMA` in
`backend/app/services/storage.py`. If future tasks need destructive schema
changes, add a planned migration mechanism before changing production data
shape.

---

## Naming Conventions

- Tables and columns use `snake_case`.
- API IDs remain documented string IDs such as `inspection-YYYYMMDD-0001`,
  `result-000001`, `fault-000001`, `alarm-000001`, `advice-000001`.
- JSON columns end in `_json`.

---

## Common Mistakes

- Do not delete or recreate SQLite files after opening a connection on Windows;
  create test databases at unique temp paths before constructing `SQLiteStore`.
- Do not store frontend-only field names such as `downloadUrl` in report list
  rows; backend report list uses `reportStatus`, `createdAt`, and `url`.
