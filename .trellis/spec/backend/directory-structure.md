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

- Route modules:
  - `backend/app/api/routes/health.py` exposes `/api/health`.
  - `backend/app/api/routes/system.py` exposes system/demo status endpoints.
  - `backend/app/api/routes/inspections.py` exposes inspection lifecycle and
    detection upload endpoints.
  - `backend/app/api/routes/assets.py` exposes devices, faults, alarms, events,
    and process-status updates.
  - `backend/app/api/routes/camera.py` exposes the read-only MJPEG camera stream.
- Router registration:
  - `backend/app/api/router.py` imports route modules and assigns path prefixes.
- Models:
  - `backend/app/models/system.py` owns system/demo status models.
  - `backend/app/models/inspection.py` owns inspection, detection, fault, alarm,
    advice, report, and pagination models.
  - `backend/app/models/responses.py` owns `ApiResponse[T]` and error payloads.
- Services:
  - `backend/app/services/demo_data.py` owns initial demo data helpers.
  - `backend/app/services/inspection_service.py` owns database-backed business
    behavior.
  - `backend/app/services/storage.py` owns SQLite schema setup and compatibility
    column additions.
  - `backend/app/services/camera_bridge.py` owns backend camera capture,
    streaming, sampling, and outbox fallback behavior.
- Tests:
  - `backend/tests/test_member4_api.py` covers the end-to-end detection,
    advice, report, and dashboard flow.
  - `backend/tests/test_camera_bridge.py` covers camera bridge helpers.
  - `backend/tests/test_camera_stream_api.py` covers camera stream routing.
  - `backend/tests/conftest.py` resets an isolated SQLite database for every
    test and disables hardware-dependent background workers.

---

## Wrong vs Correct

### Wrong

```python
# backend/app/api/routes/reports.py
connection = sqlite3.connect("data/edgeeye.db")
rows = connection.execute("SELECT * FROM reports").fetchall()
```

### Correct

```python
@router.get("/reports", response_model=ApiResponse[PageResult[ReportListItem]])
def list_reports(page: int = 1, pageSize: int = 20) -> ApiResponse[PageResult[ReportListItem]]:
    return ApiResponse(
        data=get_service().list_reports(page=page, page_size=pageSize),
        timestamp=current_timestamp(),
    )
```

Route files own HTTP shape; `InspectionService` owns persistence and business
logic.

## Scenario: Built-in Camera Bridge Service

### 1. Scope / Trigger

- Trigger: backend-owned infrastructure that captures USB camera frames for the
  realtime milestone and optionally runs sampled frames through the Atlas OM
  bridge.
- Applies when adding startup/shutdown workers, camera capture helpers, or
  backend-visible image writers.

### 2. Signatures

- Service module: `backend/app/services/camera_bridge.py`.
- Model subprocess wrapper: `backend/app/services/edge_model.py`.
- Lifecycle entry point: `camera_bridge_service.start()` in `app.main.lifespan`;
  `camera_bridge_service.stop()` in lifespan shutdown.
- Display route: `GET /api/camera/stream.mjpg` lives in
  `backend/app/api/routes/camera.py` and returns `StreamingResponse` with
  `multipart/x-mixed-replace; boundary=frame`.
- Persistence boundary: call `get_service().upload_detection_result(payload)`
  with an existing `DetectionUploadRequest`; do not create a camera upload route
  or change `POST /api/detection/results` for this bridge.

### 3. Contracts

- Environment keys use the existing `EDGEEYE_` prefix:
  `CAMERA_BRIDGE_ENABLED`, `CAMERA_SOURCE`, `CAMERA_CAPTURE_BACKEND`,
  `CAMERA_FFMPEG_PATH`, `CAMERA_V4L2_CTL_PATH`, `CAMERA_WIDTH`,
  `CAMERA_HEIGHT`, `CAMERA_INTERVAL_SECONDS`, `CAMERA_STREAM_FPS`,
  `CAMERA_TIMEOUT_SECONDS`, `CAMERA_MAX_RAW_FRAMES_PER_INSPECTION`,
  `CAMERA_DEVICE_ID`, `CAMERA_OPERATOR`, and `CAMERA_OUTBOX_DIR`.
- Sampled model inference uses `EDGEEYE_` env keys:
  `EDGE_MODEL_ENABLED`, `EDGE_MODEL_PYTHON`, `EDGE_MODEL_SCRIPT`,
  `EDGE_MODEL_PATH`, `EDGE_MODEL_CLASSES_PATH`,
  `EDGE_MODEL_PREPROCESS_PATH`, `EDGE_MODEL_OUTPUT_SHAPE`,
  `EDGE_MODEL_DEVICE_ID`, `EDGE_MODEL_TIMEOUT_SECONDS`, and
  `EDGE_MODEL_ANNOTATED_ENABLED`.
- Realtime display frames are served from the in-memory MJPEG stream and are not
  persisted one file per video frame.
- Raw frames must be saved under
  `uploads/raw/{inspectionId}/{frameId}.jpg` and exposed as
  `/uploads/raw/{inspectionId}/{frameId}.jpg` only for sampled latest-result /
  evidence frames.
- When model inference succeeds, annotated frames are saved under
  `uploads/annotated/{inspectionId}/{frameId}.jpg`, `detections` comes from
  the bridge output, and `annotatedImageUrl` is the matching `/uploads/...`
  URL.
- When model inference is disabled or unavailable, the bridge writes
  `detections: []`, `annotatedImageUrl: null`, `uploadReason: periodic_sample`,
  and `performance.npuUsage: null`.
- If `uv run` shadows `python3` with `backend/.venv/bin/python3`, the model
  subprocess must resolve to a system Python that can import board-provided
  `cv2`, `numpy`, and `acl`.

### 4. Validation & Error Matrix

- `CAMERA_BRIDGE_ENABLED=false` -> do not start a background thread.
- `/dev/*` camera source missing -> log and skip startup without failing API
  startup.
- `GET /api/camera/stream.mjpg` when disabled/missing camera/ffmpeg -> return
  `CAMERA_STREAM_UNAVAILABLE` with HTTP 503 before streaming starts.
- capture command failure -> log warning and continue the loop.
- missing model/script/classes/preprocess path -> log once and upload the
  sampled frame as empty detections.
- model subprocess timeout/non-zero exit/invalid JSON -> log once and upload
  the sampled frame as empty detections.
- upload failure after payload construction -> write JSON to
  `CAMERA_OUTBOX_DIR`.
- raw sample count over `CAMERA_MAX_RAW_FRAMES_PER_INSPECTION` -> delete oldest
  no-model raw sample files for that inspection.
- annotated sample count over `CAMERA_MAX_RAW_FRAMES_PER_INSPECTION` -> delete
  oldest annotated sample files for that inspection.

### 5. Good/Base/Bad Cases

- Good: service code owns capture, in-memory streaming, low-frequency sampling,
  optional sampled-frame model inference, annotation, and payload building; the
  only camera route is the read-only MJPEG display route.
- Base: backend starts without a camera and still serves all APIs.
- Bad: importing `cv2`, `numpy`, or `acl` at FastAPI import time so backend
  tests or startup fail on machines without board runtime packages.
- Bad: adding a third required startup command for the realtime bridge.

### 6. Tests Required

- Unit tests for frame ID/path helpers and payload fields.
- Unit tests for model subprocess JSON parsing, path resolution, and graceful
  disabled/missing-resource behavior.
- Unit tests for MJPEG part framing, JPEG chunk extraction, and raw-frame
  retention pruning.
- Route tests for `/api/camera/stream.mjpg` success-path media type and 503
  unavailable errors.
- Backend tests must disable the bridge in `tests/conftest.py` so pytest never
  depends on USB hardware.
- Smoke test with real hardware should query latest-result twice and verify
  `frameId` changes while `/api/camera/stream.mjpg` stays open.

### 7. Wrong vs Correct

#### Wrong

```python
@router.post("/camera/frame")
def upload_camera_frame(...):
    ...
```

#### Correct

```python
@router.get("/camera/stream.mjpg")
def stream_camera() -> StreamingResponse:
    return StreamingResponse(camera_bridge_service.iter_mjpeg_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

payload = build_camera_payload(...)
get_service().upload_detection_result(payload)
```

#### Wrong

```python
import cv2
import acl

def start() -> None:
    ...
```

This makes backend import depend on Atlas runtime packages.

#### Correct

```python
result = edge_model_service.infer_frame(captured.path, annotated_path)
payload = build_camera_payload(..., detections=result.detections if result else [])
```

The model path is optional and failure degrades one sample, not the API process
or MJPEG stream.
