# Directory Structure

> How backend code is organized in this project.

---

## Overview

Backend code lives in `backend/` and uses FastAPI. Keep route handlers thin:
routes should validate HTTP input/output and call service functions; business
logic and later database access should not be embedded directly in route files.

---

## Directory Layout

```text
backend/
├── app/
│   ├── main.py              # FastAPI app creation and middleware wiring
│   ├── api/
│   │   ├── router.py        # top-level /api router registration
│   │   └── routes/          # route modules grouped by API domain
│   ├── core/                # settings and app-wide helpers
│   ├── models/              # Pydantic API models and shared enum literals
│   └── services/            # business/demo data services
├── tests/                   # pytest tests for API behavior
├── pyproject.toml
└── uv.lock
```

---

## Module Organization

- Add new HTTP endpoints under `backend/app/api/routes/<domain>.py`.
- Register route modules only in `backend/app/api/router.py`.
- Put API request/response schemas in `backend/app/models/`.
- Put implementation logic in `backend/app/services/` so it can later move from demo data to database-backed repositories without changing route signatures.
- Keep shared enum-like strings in `backend/app/models/common.py`.

---

## Naming Conventions

- Python files and directories use `snake_case`.
- JSON-facing Pydantic fields use `camelCase`, matching `docs/contracts.md`.
- Route function names should describe the endpoint action, for example `get_system_status`.
- Test files use `test_<domain>.py`.

---

## Examples

- `backend/app/api/routes/health.py`
- `backend/app/api/routes/system.py`
- `backend/app/models/system.py`
- `backend/app/services/demo_data.py`

## Scenario: Built-in Camera Bridge Service

### 1. Scope / Trigger

- Trigger: backend-owned infrastructure that captures USB camera frames for the
  no-model realtime milestone.
- Applies when adding startup/shutdown workers, camera capture helpers, or
  backend-visible image writers.

### 2. Signatures

- Service module: `backend/app/services/camera_bridge.py`.
- Lifecycle entry point: `camera_bridge_service.start()` in `app.main.lifespan`;
  `camera_bridge_service.stop()` in lifespan shutdown.
- Persistence boundary: call `get_service().upload_detection_result(payload)`
  with an existing `DetectionUploadRequest`; do not create a new HTTP route for
  this bridge.

### 3. Contracts

- Environment keys use the existing `EDGEEYE_` prefix:
  `CAMERA_BRIDGE_ENABLED`, `CAMERA_SOURCE`, `CAMERA_CAPTURE_BACKEND`,
  `CAMERA_FFMPEG_PATH`, `CAMERA_V4L2_CTL_PATH`, `CAMERA_WIDTH`,
  `CAMERA_HEIGHT`, `CAMERA_INTERVAL_SECONDS`, `CAMERA_TIMEOUT_SECONDS`,
  `CAMERA_DEVICE_ID`, `CAMERA_OPERATOR`, and `CAMERA_OUTBOX_DIR`.
- Raw frames must be saved under
  `uploads/raw/{inspectionId}/{frameId}.jpg` and exposed as
  `/uploads/raw/{inspectionId}/{frameId}.jpg`.
- The no-model bridge writes `detections: []`, `annotatedImageUrl: null`,
  `uploadReason: periodic_sample`, and `performance.npuUsage: null`.

### 4. Validation & Error Matrix

- `CAMERA_BRIDGE_ENABLED=false` -> do not start a background thread.
- `/dev/*` camera source missing -> log and skip startup without failing API
  startup.
- capture command failure -> log warning and continue the loop.
- upload failure after payload construction -> write JSON to
  `CAMERA_OUTBOX_DIR`.

### 5. Good/Base/Bad Cases

- Good: service code owns capture and payload building; routes remain unchanged.
- Base: backend starts without a camera and still serves all APIs.
- Bad: adding a third required startup command for the no-model realtime bridge.

### 6. Tests Required

- Unit tests for frame ID/path helpers and payload fields.
- Backend tests must disable the bridge in `tests/conftest.py` so pytest never
  depends on USB hardware.
- Smoke test with real hardware should query latest-result twice and verify
  `frameId` changes.

### 7. Wrong vs Correct

#### Wrong

```python
@router.post("/camera/frame")
def upload_camera_frame(...):
    ...
```

#### Correct

```python
payload = build_camera_payload(...)
get_service().upload_detection_result(payload)
```
