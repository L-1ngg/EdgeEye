# 成员1：Atlas 开发板与边缘推理设计

## Architecture

边缘端按可替换模块拆分，优先保证最小联调链路可跑通：

```text
config
  ↓
camera/video source
  ↓
preprocess
  ↓
model runner
  ├─ Atlas ACL/OM runner
  └─ local debug/mock runner
  ↓
YOLO postprocess
  ↓
key-frame selector
  ↓
image writer + annotation writer
  ↓
outbox queue
  ↓
backend uploader
```

第一版实现应避免把摄像头读取、推理、后处理和上传写成一个不可拆分脚本。核心理由是开发板环境、模型资产和后端联调通常不会同时就绪，需要能分别验证和替换。

2026-06-18 小阶段只确认摄像头硬件和前后端接口，不修改模型资产、模型 runner 或推理后处理。当前证据显示 V4L2 可从 `/dev/video0` 抓取 MJPG `640x480` 帧，但当前系统 Python/OpenCV 无法直接打开 `/dev/video0`；因此 Phase 2 实现摄像头输入时必须把 capture backend 设计成可替换，不要把业务链路绑定到单一 OpenCV `VideoCapture` 路径。

## Proposed Directories

```text
edge-app/
  edge_app/
    config.py
    camera.py
    preprocess.py
    runner.py
    postprocess.py
    keyframes.py
    payload.py
    outbox.py
    uploader.py
    health.py
    main.py
  config/
    default.yaml
    local.example.yaml
  tests/
camera/
  README.md
model-deploy/
  README.md
  atc/
  models/
logs/
```

The exact package shape can be adjusted after inspecting existing files during Phase 2. The directory names should stay aligned with `docs/engineering-standards.md`.

## Data Flow

1. Load configuration from defaults plus local override.
2. Open camera source, video file, RTSP stream, or image sequence.
3. For each frame, assign `frameSeq`, `frameId`, `timestamp`, `imageWidth`, and `imageHeight`.
4. Run preprocessing according to model config.
5. Run model inference through ACL/OM on Atlas. If Atlas runtime is not available during early integration, use a debug runner behind the same interface.
6. Decode YOLO output, apply confidence filtering and NMS, map boxes back to original image dimensions, and map model classes to EdgeEye enums.
7. Decide whether the frame is a key frame using upload reason rules.
8. Save raw and annotated images.
9. Build `DetectionUploadRequest`.
10. Put payload into local outbox before network upload.
11. Upload to `POST /api/detection/results`.
12. Mark outbox item acknowledged only after backend returns success.

当前前后端对接入口已经存在：边缘端只负责上传关键帧检测 JSON 到 `POST /api/detection/results`；前端实时页面不直接读摄像头，而是通过后端 `GET /api/inspections/{inspectionId}/latest-result` 获取 `annotatedImageUrl ?? imageUrl`、`detections` 和 `performance` 后展示。

## Contracts

Upload payload must follow `docs/contracts.md` and `docs/openapi.yaml`:

- `idempotencyKey`: default `{inspectionId}:{frameId}`
- `inspectionId`: active inspection ID from backend or configured demo inspection
- `frameId`: `frame-000001` style monotonically increasing ID
- `timestamp`: ISO 8601 with timezone
- `isKeyFrame`: true for uploaded frames
- `uploadReason`: one of `periodic_sample`, `fault_started`, `fault_updated`, `fault_resolved`, `manual_capture`, `system_event`
- `sampleWindow`: include observed time window and frame count when available
- `imageUrl` and `annotatedImageUrl`: `/uploads/raw/...` and `/uploads/annotated/...`
- `detections`: Atlas-side detection objects only; no `faults`, `alarms`, or `advice`
- `performance`: latency, fps, cpu, memory, npu

Backend validation currently accepts `performance.npuUsage = null` and rejects bbox values outside the uploaded image dimensions. Repeated uploads with the same `idempotencyKey` and identical body return `duplicate=true`; same key with different body returns `IDEMPOTENCY_CONFLICT`.

## Class Mapping

Model classes from `classes.json` must map to EdgeEye enums:

- `type: "device"` maps to `deviceType`
- `type: "fault"` or `type: "environment"` maps to `faultType`
- Unknown or unmapped values use `unknown` or `null`; do not invent new enum values during implementation.

The mapper should reject invalid bbox values and clamp only when the reason is explicit coordinate rounding. Structural output errors should be logged.

## Key-Frame Strategy

Minimum behavior:

- Normal state: upload at most one `periodic_sample` frame per second.
- New fault/environment event: upload immediately as `fault_started`.
- Ongoing event: upload at most one `fault_updated` frame every 5 seconds.
- Resolved event: upload one `fault_resolved` frame.
- Similar frame filtering: same classes, IoU greater than `0.9`, and unchanged risk/event state means no upload unless periodic interval is reached.

If risk rules are not available on the edge side, the first implementation can use class presence as the event state and leave risk decisions to the backend.

## Error Handling

- Camera open/read failures should update health state and retry with backoff.
- Model load failures should log model path, input shape, device ID, CANN/ACL version if known, and stop inference cleanly.
- ACL errors should include operation name, model path, shape, buffer byte count, and returned error code.
- Upload failures should not stop frame processing; payload stays in outbox for retry.
- Idempotency conflict should be logged as contract or retry-data mismatch and should not overwrite local acknowledged state.

## Local Health

The local health surface can be an HTTP endpoint or CLI status command. It should report:

- camera status and last frame time
- model path, classes path, and model version
- ACL/CANN initialization state
- latest latency and FPS
- outbox pending count
- backend health or latest upload status

## Operational Notes

- The first runnable milestone should accept a video file source so development can continue when the physical camera is unavailable.
- For the USB camera milestone, prefer a source abstraction that can use V4L2/ffmpeg/GStreamer when OpenCV `VideoCapture` fails on the board.
- ACL/OM runner should be isolated behind an interface so the rest of the pipeline can be tested off-board.
- Real secrets must not be committed. Local endpoints and credentials belong in local config, not default config.
- Rollback is simple at Phase 2 granularity: keep debug runner and sample video path working while adding Atlas-specific code.
