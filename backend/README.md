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

When `/dev/video0` is present, the backend also starts a camera bridge in the
same process. The bridge keeps one ffmpeg MJPEG reader open, exposes
`GET /api/camera/stream.mjpg` for the frontend live view, periodically saves a
bounded raw-frame sample under `/uploads/raw/{inspectionId}/{frameId}.jpg`, and
tries to run the configured Atlas OM model for that sample. Successful model
results populate the existing `detections` field and save
`/uploads/annotated/{inspectionId}/{frameId}.jpg`; model failures degrade to an
empty-detection sample without stopping the realtime stream. The bridge does
not continuously record MP4 files or save every video frame.

## Configuration

Environment variables use the `EDGEEYE_` prefix:

- `EDGEEYE_DATABASE_PATH`: SQLite database path. Defaults to `data/edgeeye.db`.
- `EDGEEYE_UPLOADS_DIR`: local static root served at `/uploads`. Defaults to `uploads`.
- `EDGEEYE_REPORTS_DIR`: local static root served at `/reports`. Defaults to `reports`.
- `EDGEEYE_CAMERA_BRIDGE_ENABLED`: start the built-in camera bridge. Defaults to `true`.
- `EDGEEYE_CAMERA_SOURCE`: camera source. Defaults to `/dev/video0`.
- `EDGEEYE_CAMERA_CAPTURE_BACKEND`: `ffmpeg`, `v4l2`, or `auto`. Defaults to `ffmpeg`.
- `EDGEEYE_CAMERA_INTERVAL_SECONDS`: sample/evidence interval for latest-result. Defaults to `5.0`.
- `EDGEEYE_CAMERA_STREAM_FPS`: MJPEG live-view frame rate. Defaults to `30`.
- `EDGEEYE_CAMERA_MAX_RAW_FRAMES_PER_INSPECTION`: maximum retained no-model raw samples per inspection. Defaults to `120`.
- `EDGEEYE_EDGE_MODEL_ENABLED`: run Atlas OM inference on sampled camera frames. Defaults to `true`.
- `EDGEEYE_EDGE_MODEL_PYTHON`: Python executable used for the ACL bridge script. Use a system Python with `cv2`, `numpy`, and `acl`; the current board uses `/usr/local/miniconda3/bin/python3`.
- `EDGEEYE_EDGE_MODEL_SCRIPT`: one-frame ACL bridge script. Defaults to `model-deploy/edge_acl_om_bridge.py`.
- `EDGEEYE_EDGE_MODEL_PATH`: OM model path. Defaults to the insulator domain-r1 OM artifact.
- `EDGEEYE_EDGE_MODEL_CLASSES_PATH`: class mapping JSON for backend detection enums.
- `EDGEEYE_EDGE_MODEL_PREPROCESS_PATH`: model preprocessing and threshold JSON.
- `EDGEEYE_EDGE_MODEL_OUTPUT_SHAPE`: YOLO output tensor shape. Defaults to `1,6,8400`.
- `EDGEEYE_EDGE_MODEL_DEVICE_ID`: Atlas device id. Defaults to `0`.
- `EDGEEYE_EDGE_MODEL_ANNOTATED_ENABLED`: save annotated sample images. Defaults to `true`.
- `EDGEEYE_LLM_PROVIDER`: provider selector. Use `rule-template`, `deepseek`, or `openai-compatible`. Defaults to `rule-template`.
- `EDGEEYE_LLM_API_URL`: optional OpenAI-compatible chat-completions endpoint. With `deepseek`, leave it empty to use the official DeepSeek endpoint.
- `EDGEEYE_LLM_API_KEY`: optional backend-only LLM API key. It is never returned to the frontend.
- `EDGEEYE_LLM_MODEL_NAME`: model name sent to the provider and saved on advice. With `deepseek`, leave the default to use `deepseek-v4-pro`.
- `EDGEEYE_LLM_TIMEOUT_SECONDS`: timeout for provider calls.
- `EDGEEYE_LLM_MAX_RETRIES`: retry count before rule-template fallback.
- `EDGEEYE_ALARM_DEDUP_WINDOW_SECONDS`: window (seconds) within which a duplicate alarm key is suppressed instead of reopened. Defaults to `300`.

See `.env.example` for a copyable template.

When no provider is configured or the provider call fails, `POST /api/advice/generate` saves and returns a complete rule-template fallback advice object.

DeepSeek local example:

```env
EDGEEYE_LLM_PROVIDER=deepseek
EDGEEYE_LLM_API_KEY=<your-deepseek-api-key>
```

## Atlas Integration Notes

- `POST /api/detection/results` accepts JSON only. Do not send multipart data to this endpoint.
- Atlas should save raw and annotated images under a backend-visible location and submit URLs such as `/uploads/raw/{inspectionId}/{frameId}.jpg` and `/uploads/annotated/{inspectionId}/{frameId}.jpg`.
- The backend serves `EDGEEYE_UPLOADS_DIR` at `/uploads` and `EDGEEYE_REPORTS_DIR` at `/reports`.
- Every detection bbox is validated against the uploaded image dimensions: `0 <= x1 < x2 <= imageWidth` and `0 <= y1 < y2 <= imageHeight`.
- `performance.npuUsage` may be `null` when board-side NPU metrics are unavailable.
- The built-in camera bridge runs real YOLO/Atlas inference on sampled frames when the configured OM and pyACL runtime are available. It still uses the existing detection upload route and falls back to empty detections if model inference is unavailable.
- The realtime frontend should use `GET /api/camera/stream.mjpg` for smooth display and keep `GET /api/inspections/{id}/latest-result` for detection boxes, faults, performance, and report evidence references.

## Member 4 Endpoints

- Inspections: `POST /api/inspection/start`, `POST /api/inspections/{id}/finish`, `POST /api/inspections/{id}/fail`, `GET /api/inspections`, `GET /api/inspections/{id}/latest-result`
- Camera stream: `GET /api/camera/stream.mjpg`
- Detection upload: `POST /api/detection/results`
- Fault center: `GET /api/devices`, `GET /api/faults`, `GET /api/alarms`, `GET /api/events`, `PATCH /api/faults/{id}/status`, `PATCH /api/alarms/{id}/status`
- Advice: `POST /api/advice/generate`, `GET /api/faults/{id}/advice`
- Reports: `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/export`

## Test

```bash
uv run pytest
```
