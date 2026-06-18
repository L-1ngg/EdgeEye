# EdgeEye Backend

FastAPI service for EdgeEye member 4 work: API, SQLite persistence, dashboard data, system status, alarms, reports, and backend repair advice generation.

## Run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Default API base URL:

```text
http://localhost:8000/api
```

When `/dev/video0` is present, the backend also starts a no-model camera bridge
in the same process. The bridge captures frames with ffmpeg by default, saves
them under `/uploads/raw/{inspectionId}/{frameId}.jpg`, and writes empty
`detections` results through the existing backend service so the frontend
realtime page can show live camera frames without a separate edge process.

## Configuration

Environment variables use the `EDGEEYE_` prefix:

- `EDGEEYE_DATABASE_PATH`: SQLite database path. Defaults to `data/edgeeye.db`.
- `EDGEEYE_UPLOADS_DIR`: local static root served at `/uploads`. Defaults to `uploads`.
- `EDGEEYE_REPORTS_DIR`: local static root served at `/reports`. Defaults to `reports`.
- `EDGEEYE_CAMERA_BRIDGE_ENABLED`: start the built-in camera bridge. Defaults to `true`.
- `EDGEEYE_CAMERA_SOURCE`: camera source. Defaults to `/dev/video0`.
- `EDGEEYE_CAMERA_CAPTURE_BACKEND`: `ffmpeg`, `v4l2`, or `auto`. Defaults to `ffmpeg`.
- `EDGEEYE_CAMERA_INTERVAL_SECONDS`: target capture interval. Defaults to `1.0`.
- `EDGEEYE_LLM_PROVIDER`: reserved provider selector. Defaults to `rule-template`.
- `EDGEEYE_LLM_API_URL`: optional OpenAI-compatible chat-completions endpoint.
- `EDGEEYE_LLM_API_KEY`: optional backend-only LLM API key. It is never returned to the frontend.
- `EDGEEYE_LLM_MODEL_NAME`: model name metadata for future provider calls.
- `EDGEEYE_LLM_TIMEOUT_SECONDS`: timeout for provider calls.
- `EDGEEYE_LLM_MAX_RETRIES`: retry count before rule-template fallback.
- `EDGEEYE_ALARM_DEDUP_WINDOW_SECONDS`: window (seconds) within which a duplicate alarm key is suppressed instead of reopened. Defaults to `300`.

See `.env.example` for a copyable template.

When no provider is configured or the provider call fails, `POST /api/advice/generate` saves and returns a complete rule-template fallback advice object.

## Atlas Integration Notes

- `POST /api/detection/results` accepts JSON only. Do not send multipart data to this endpoint.
- Atlas should save raw and annotated images under a backend-visible location and submit URLs such as `/uploads/raw/{inspectionId}/{frameId}.jpg` and `/uploads/annotated/{inspectionId}/{frameId}.jpg`.
- The backend serves `EDGEEYE_UPLOADS_DIR` at `/uploads` and `EDGEEYE_REPORTS_DIR` at `/reports`.
- Every detection bbox is validated against the uploaded image dimensions: `0 <= x1 < x2 <= imageWidth` and `0 <= y1 < y2 <= imageHeight`.
- `performance.npuUsage` may be `null` when board-side NPU metrics are unavailable.
- The built-in camera bridge is only a no-model realtime display bridge. Real YOLO/Atlas inference should later populate the existing `detections` field without changing the upload route.

## Member 4 Endpoints

- Inspections: `POST /api/inspection/start`, `POST /api/inspections/{id}/finish`, `POST /api/inspections/{id}/fail`, `GET /api/inspections`, `GET /api/inspections/{id}/latest-result`
- Detection upload: `POST /api/detection/results`
- Fault center: `GET /api/devices`, `GET /api/faults`, `GET /api/alarms`, `GET /api/events`, `PATCH /api/faults/{id}/status`, `PATCH /api/alarms/{id}/status`
- Advice: `POST /api/advice/generate`, `GET /api/faults/{id}/advice`
- Reports: `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/export`

## Test

```bash
uv run pytest
```
