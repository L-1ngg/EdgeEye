# 成员1：Atlas 开发板与边缘推理实施计划

## Phase 0: Board Facts

- [x] Ask user to collect Atlas board facts: board model, OS, CANN version, Python version, camera type, network reachability.
- [x] Re-check USB camera after repository update: `/dev/video0` is present and V4L2 can capture MJPG `640x480` test frame.
- [x] Resolve or route around current OpenCV `VideoCapture('/dev/video0', cv2.CAP_V4L2)` open failure before relying on OpenCV for continuous capture.
- [x] Record current test model metadata from teammate: YOLOv8 detect, one class `0: transformer`, input `640x640`, `conf=0.25`, `iou=0.45`; ATC/OM/ACL remains pending.
- [x] Record current insulator domain-r1 candidate metadata from teammate: YOLOv8 detect, two classes `insulator_normal` and `insulator_surface_damage`, input `640x640`, `conf=0.25`, `iou=0.45`.
- [ ] Ask user to confirm backend base URL reachable from board.
- [x] Record current temporary ONNX asset path and model limits: `models/artifacts/detector-transformer-v1.onnx` is a one-class `transformer` detect model and remains a local ignored artifact.
- [x] Record current insulator ONNX/PT artifact paths and hashes: `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.onnx` and `.pt` are local ignored artifacts and match `dataset/docs/edgeeye-insulator-v1-domain-r1-report.md`.

## Phase 1: Repository Inspection Before Code

- [x] Load `trellis-before-dev` before any business-code edit.
- [ ] Read relevant project specs and docs:
  - `docs/01-edge-atlas.md`
  - `docs/contracts.md`
  - `docs/openapi.yaml`
  - `docs/api-spec.md`
  - `docs/engineering-standards.md`
  - `docs/interfaces-and-deliverables.md`
- [x] Search for existing `edge-app`, `camera`, `model-deploy`, upload helpers, or sample payloads before creating new code.
- [x] Confirm backend upload route exists at `POST /api/detection/results` and frontend realtime page consumes `GET /api/inspections/{inspectionId}/latest-result`.
- [x] Confirm current stage should not modify model assets, model runner, model inference, or postprocess logic.

## Phase 2: Skeleton and Config

- [x] Move the no-model realtime bridge into the backend process so only backend and frontend startup commands are required.
- [x] Add backend configuration covering camera source, capture backend, upload paths, and key-frame timing for the no-model realtime bridge.
- [x] Add backend configuration for MJPEG stream FPS, low-frequency sample interval, and bounded raw-frame retention.
- [x] Add typed config loading with clear validation errors.
- [x] Add logging setup with structured fields aligned to engineering standards.

## Phase 3: Frame Input

- [x] Implement video/camera source abstraction for ffmpeg and V4L2 capture.
- [x] Support single-frame capture command for hardware smoke test.
- [x] Support continuous frame iteration with retry logging.
- [x] Save sampled raw frames using `raw/{inspectionId}/{frameId}.jpg`; do not save every realtime video frame.

## Phase 4: Model Runner and Postprocess

- [x] Add a local ONNX debug bridge for image-based inference and payload generation: `model-deploy/edge_onnx_bridge.py`.
- [x] Add current model metadata files: `model-deploy/classes-v1.json`, `model-deploy/label.names`, and `model-deploy/preprocess-v1.json`.
- [x] Update current temporary model threshold to `conf=0.25` and keep NMS IoU at `0.45`.
- [x] Add `model-deploy/expected-output-v1.json` as the 5-image ONNX smoke baseline for future OM/ACL comparison.
- [x] Update `.trellis/spec/backend/detection-upload-adapters.md` with the local smoke baseline artifact convention.
- [ ] Implement a common runner interface for the final edge process.
- [ ] Implement debug/mock runner first if Atlas runtime cannot be verified in this environment.
- [x] Implement one-frame ACL/OM bridge on board once user confirms CANN/ACL availability:
  `model-deploy/edge_acl_om_bridge.py`.
- [x] Implement preprocessing for the ACL bridge: BGR to RGB, resize/letterbox,
  normalize, HWC to CHW, batch dimension.
- [x] Implement YOLO output decoding, confidence filter, coordinate scaling,
  NMS, and class mapping for the ACL bridge by reusing the ONNX bridge helpers.
- [x] Validate local ONNX debug bridge output against backend `DetectionUploadRequest`.
- [x] Validate the 5 local teammate-provided test images through the ONNX debug bridge; generated payloads all pass backend request model validation.
- [x] Add tracked insulator candidate deploy metadata:
  `classes-edgeeye-insulator-v1.json`,
  `label-edgeeye-insulator-v1.names`,
  `preprocess-edgeeye-insulator-v1.json`, and
  `expected-output-edgeeye-insulator-v1.json`.
- [x] Validate insulator candidate JSON metadata and label/class order.
- [x] Convert the insulator candidate ONNX to OM with ATC after user confirmation.
- [x] Inspect the generated OM model info.
- [x] Run minimal pyACL execution smoke and confirm output shape `[1,6,8400]`.
- [ ] Compare OM/ACL output with `model-deploy/expected-output-edgeeye-insulator-v1.json`; blocked until the ignored `dataset/processed/...` fixture images are available locally.
- [x] Validate bbox and enum output in the backend sampled-frame path before upload via
  `DetectionUploadRequest` and focused pytest coverage.

## Phase 5: Key Frames, Annotation, Upload

- [x] Implement annotation writer and save `annotated/{inspectionId}/{frameId}.jpg` in the backend sampled-frame path.
- [x] Generate local annotated smoke images through `edge_onnx_bridge.py` under ignored `model-deploy/artifacts/transformer-v1-test-images/annotated/`.
- [ ] Implement key-frame selector for periodic, started, updated, resolved, manual, and system-event reasons.
- [x] Implement payload builder matching `DetectionUploadRequest` with empty `detections` for no-model realtime display inside backend service code.
- [x] Implement payload builder matching `DetectionUploadRequest` with model detections in the local ONNX debug bridge.
- [x] Extend the backend camera payload builder to accept model detections and
  `annotatedImageUrl` without changing the upload API.
- [x] Implement local outbox save on upload failure.
- [x] Reuse the backend `InspectionService.upload_detection_result` path for
  sampled-frame uploads, including existing idempotency behavior.

## Phase 6: Health and Operations

- [x] Add frontend realtime display through backend MJPEG stream while keeping latest-result polling for metadata.
- [x] Add bounded raw-frame retention for no-model samples.
- [x] Add backend model configuration for OM path, class/preprocess JSON,
  output shape, Atlas device id, annotated image toggle, and system Python path.
- [ ] Add local health surface reporting camera, model, ACL, performance, outbox, and backend status.
- [ ] Add clear startup and shutdown lifecycle, releasing camera/model/ACL resources.
- [ ] Add board-side runbook for environment checks, model conversion, startup, and common failures.

## Validation Commands

Run commands will be finalized after the edge package structure exists. Expected checks:

```bash
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/task.py current --source
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
cd web && bun run build
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -sS http://127.0.0.1:8000/api/health
curl -sS --max-time 2 http://127.0.0.1:8000/api/camera/stream.mjpg >/tmp/edgeeye-stream-smoke.mjpg
curl -sS http://127.0.0.1:8000/api/inspections?pageSize=1
```

Commands already run for the 2026-06-18 camera/interface smoke stage:

```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video0 --list-formats-ext
v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=1 --stream-to=/tmp/edgeeye-video0-frame.mjpg
python3 -c "import cv2; cap=cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2); print(cap.isOpened()); cap.release()"
env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
```

Results:

- V4L2 direct capture succeeded and produced `camera-usb-video0-2026-06-18-v4l2.jpg`.
- Current OpenCV direct camera open failed, so this remains an implementation risk.
- Backend tests passed: `11 passed, 1 warning`.

Commands run for the 2026-06-18 no-model realtime camera bridge before backend integration:

```bash
python3 -m py_compile edge-app/edge_app/live_camera.py edge-app/tests/test_live_camera.py
PYTHONPATH=edge-app python3 -m unittest discover -s edge-app/tests
PYTHONPATH=edge-app python3 -m edge_app.live_camera --config edge-app/config/local.example.json --once --dry-run
PYTHONPATH=edge-app python3 -m edge_app.live_camera --config edge-app/config/local.example.json --backend-url http://127.0.0.1:8000/api --max-frames 2
curl -sS http://127.0.0.1:8000/api/inspections/inspection-20260618-0002/latest-result
```

Results:

- Unit tests passed: `Ran 3 tests ... OK`.
- Dry-run generated a valid upload payload and saved a frame.
- Real upload created `inspection-20260618-0002`, uploaded `frame-000001` and `frame-000002`, and latest-result returned the latest frame URL and empty detection list.

Current integration direction:

- The standalone `edge-app` bridge is removed.
- The backend starts the camera bridge from `app.main` startup hooks.
- Backend tests set `settings.camera_bridge_enabled = False` to keep hardware out of pytest.
- The frontend uses `/api/camera/stream.mjpg` for smooth live video and polls latest-result every 1 second for metadata, so users only start backend and frontend.
- The backend no longer saves every displayed frame. It samples raw frames at `EDGEEYE_CAMERA_INTERVAL_SECONDS` and prunes old no-model samples with `EDGEEYE_CAMERA_MAX_RAW_FRAMES_PER_INSPECTION`.

Commands run for the 2026-06-21 ONNX debug bridge scaffold:

```bash
python3 -m py_compile model-deploy/edge_onnx_bridge.py
python3 model-deploy/edge_onnx_bridge.py --help
python3 -m json.tool model-deploy/classes-v1.json
python3 -m json.tool model-deploy/preprocess-v1.json
unzip -p dataset/artifacts/transformer-roboflow-v2-yolov8.zip test/images/20210713_144152_jpg.rf.c57ccafabfe838548f29ca2546bc9b8a.jpg > /tmp/edgeeye-transformer-test.jpg
python3 model-deploy/edge_onnx_bridge.py --image /tmp/edgeeye-transformer-test.jpg --frame-id frame-000001 --inspection-id inspection-local-0001 --payload-output /tmp/edgeeye-payload.json
backend/.venv/bin/python -c "import json; import sys; sys.path.insert(0, 'backend'); from app.models.inspection import DetectionUploadRequest; payload=json.load(open('/tmp/edgeeye-payload.json')); DetectionUploadRequest(**payload); print('payload validation ok')"
```

Results:

- The bridge generated `transformer` detections from the current ONNX model.
- The generated payload passed backend `DetectionUploadRequest` validation.
- The current model only maps to `deviceType: transformer` and `faultType: null`; it is useful for device-box display but not fault/alarm generation.

Commands run for the 2026-06-22 teammate 5-image ONNX smoke:

```bash
python3 -m py_compile model-deploy/edge_onnx_bridge.py
python3 -m json.tool model-deploy/classes-v1.json
python3 -m json.tool model-deploy/preprocess-v1.json
python3 -m json.tool model-deploy/expected-output-v1.json
python3 model-deploy/edge_onnx_bridge.py \
  --image model-deploy/artifacts/transformer-v1-test-images/raw/transformer-v1-001.jpg \
  --frame-id frame-001 \
  --inspection-id inspection-transformer-v1-smoke \
  --annotated-output model-deploy/artifacts/transformer-v1-test-images/annotated/transformer-v1-001.jpg \
  --payload-output model-deploy/artifacts/transformer-v1-test-images/payloads/transformer-v1-001.json
backend/.venv/bin/python -c "import json, pathlib, sys; sys.path.insert(0, 'backend'); from app.models.inspection import DetectionUploadRequest; paths=sorted(pathlib.Path('model-deploy/artifacts/transformer-v1-test-images/payloads').glob('*.json')); [DetectionUploadRequest(**json.loads(path.read_text())) for path in paths]; print(f'payload validation ok: {len(paths)} files')"
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
```

Results:

- The 5 user-provided images were moved from root `images/` to ignored local artifacts at `model-deploy/artifacts/transformer-v1-test-images/raw/` and renamed `transformer-v1-001.jpg` through `transformer-v1-005.jpg`.
- The ONNX bridge generated payloads and annotated images for all 5 inputs using `conf=0.25` and `iou=0.45`.
- Backend request-model validation passed for all 5 generated payloads.
- `model-deploy/expected-output-v1.json` was compared against the generated payloads with local assertions; the baseline matched.
- Baseline summary: `transformer-v1-001` produced one `transformer` detection at confidence `0.3071`; `transformer-v1-004` produced one `transformer` detection at confidence `0.5046`; the other 3 samples produced empty `detections`, which is valid for this smoke baseline.
- Backend pytest passed: `19 passed, 1 warning`.
- ATC conversion, OM generation, Atlas ACL loading, and backend direct upload were intentionally not run in this step.

Commands run for the 2026-06-22 remote training handoff review:

```bash
git fetch origin main
git reset --hard origin/main
tar -tzf models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw-delivery.tar.gz
sha256sum \
  models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.onnx \
  models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.pt
python3 -m json.tool model-deploy/classes-edgeeye-insulator-v1.json
python3 -m json.tool model-deploy/preprocess-edgeeye-insulator-v1.json
python3 -m json.tool model-deploy/expected-output-edgeeye-insulator-v1.json
```

Results:

- Remote already contains the training workflow under `training/` and the
  authoritative insulator domain-r1 report under `dataset/docs/`.
- Delivery package contains `best.onnx`, `best.pt`, `classes.json`,
  `label.names`, `preprocess-v1.json`, `expected-output-v1.json`, and a copy of
  `dataset/docs/edgeeye-insulator-v1-domain-r1-report.md`.
- Local ONNX/PT hashes match the remote report:
  ONNX `5d9ad03c7357a3adf0c99bc31edb25d6f6fb0297f3209dc8cbc5cfdf72b71721`,
  PT `fc09697056625f0bde42f5a32a8d06543ea8031aa0b7bf2450a5d5b744a11fa8`.
- Candidate mapping is contract-valid:
  `insulator_normal -> deviceType: insulator, faultType: null` and
  `insulator_surface_damage -> deviceType: insulator, faultType: surface_damage`.
- ATC conversion, OM generation, Atlas ACL loading, and backend direct upload
  were intentionally not run in this review step; user confirmation is required
  before starting.

Next ATC command draft for the current 310B4 board:

```bash
HOME=/tmp atc \
  --model=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.onnx \
  --framework=5 \
  --output=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw \
  --input_format=NCHW \
  --input_shape="images:1,3,640,640" \
  --soc_version=Ascend310B4 \
  --output_type=FP32 \
  --log=info
```

Board-side validation commands will be provided to the user step by step and adjusted from real outputs.

Commands run for the 2026-06-22 ATC/ACL smoke:

```bash
HOME=/tmp atc \
  --model=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.onnx \
  --framework=5 \
  --output=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw \
  --input_format=NCHW \
  --input_shape="images:1,3,640,640" \
  --soc_version=Ascend310B4 \
  --output_type=FP32 \
  --log=info
atc --mode=6 \
  --om=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om
sha256sum models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om
```

Results:

- First sandboxed ATC attempt failed with `PermissionError: Operation not
  permitted`; rerunning outside the sandbox succeeded.
- Generated OM:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om`.
- OM SHA-256:
  `649934ee37b723e670773e551e169407b4057173117fc178813ea84998022d0c`.
- `atc --mode=6` reported `atc_version=7.0.0.5.242`,
  `soc_version=Ascend310B4`, `memory_size=24779264 B`, and
  `weight_size=22340096 B`.
- Minimal pyACL smoke loaded the OM, allocated input/output buffers, executed
  one all-zero input, and produced output shape `[1,6,8400]` in about
  `26.659 ms`.
- Case-by-case comparison with `expected-output-edgeeye-insulator-v1.json` is
  still pending because the referenced `dataset/processed/...` fixture images
  are ignored and absent from this checkout.

Commands run for the 2026-06-22 backend camera-to-OM integration:

```bash
python3 -m py_compile \
  model-deploy/edge_acl_om_bridge.py \
  backend/app/services/edge_model.py \
  backend/app/services/camera_bridge.py \
  backend/app/core/config.py
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
python3 model-deploy/edge_acl_om_bridge.py \
  --model models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om \
  --image backend/uploads/raw/inspection-20260622-0007/frame-000058.jpg \
  --classes model-deploy/classes-edgeeye-insulator-v1.json \
  --preprocess model-deploy/preprocess-edgeeye-insulator-v1.json \
  --annotated-output /tmp/edgeeye-om-smoke.jpg \
  --output-shape 1,6,8400
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
curl -sS http://127.0.0.1:8000/api/health
curl -sS 'http://127.0.0.1:8000/api/inspections?pageSize=1'
curl -sS http://127.0.0.1:8000/api/inspections/inspection-20260622-0010/latest-result
curl -sS --max-time 2 http://127.0.0.1:8000/api/camera/stream.mjpg -o /tmp/edgeeye-stream-smoke.mjpg -w "%{http_code} %{size_download}\n"
cd web && bun run dev --host 0.0.0.0 --port 5173
curl -sS -I http://127.0.0.1:5173/
```

Results:

- Backend pytest passed: `23 passed, 1 warning`.
- Direct ACL/OM bridge smoke on a real camera sample succeeded with output
  `imageWidth=640`, `imageHeight=480`, `latencyMs=26.294`, `fps=38.031`, and
  `detections=[]` because the current camera frame did not contain an
  insulator target.
- First backend integration attempt exposed two environment issues and both
  were fixed: `uv run` shadowed `python3` with `.venv/bin/python3` lacking
  `cv2/numpy`, and relative raw image paths were interpreted from the project
  root inside the bridge subprocess.
- Running backend now creates raw and annotated sampled frames under
  `backend/uploads/raw/inspection-20260622-0010/` and
  `backend/uploads/annotated/inspection-20260622-0010/`.
- Latest result for `inspection-20260622-0010` returned
  `annotatedImageUrl=/uploads/annotated/inspection-20260622-0010/frame-000014.jpg`,
  dimensions `640x480`, `performance.latencyMs=21.63`, and empty detections
  for the current scene.
- MJPEG stream smoke returned HTTP `200` and downloaded bytes before the
  expected long-connection timeout.
- Frontend dev server is running at `http://192.168.137.2:5173/` and returned
  HTTP `200` for the root page.

Commands run for the 2026-06-22 live camera usability hotfix:

```bash
cd backend && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run pytest
cd web && bun run build
```

Results:

- Backend camera sample save / OM inference now runs in a single background
  sample thread instead of synchronously inside the MJPEG read loop. If the
  previous sample is still running, the next sample is skipped so realtime
  streaming can continue.
- Added regression coverage for the sample scheduler busy case in
  `backend/tests/test_camera_bridge.py`.
- Frontend shell now keeps the desktop sidebar fixed in the viewport with an
  explicit collapse toggle; the workspace scrolls independently.
- Realtime camera display is constrained to a medium-width stage with lower
  minimum height so it no longer dominates the page.
- Validation passed: backend pytest `24 passed, 1 warning`; frontend production
  build passed.

## Review Gates

- [ ] User confirms board facts and available model/backend inputs.
- [ ] User reviews this PRD/design/implementation plan.
- [ ] Task is activated with `task.py start` only after review.
- [ ] Code implementation proceeds in small increments with verification after each milestone.

## Git Collaboration Cadence

- [ ] After each meaningful file update, inspect `git status --short` and create a focused commit for this task's related files.
- [ ] Keep commits scoped by milestone, for example planning, edge skeleton, camera input, model runner, upload/outbox, health/runbook.
- [ ] Do not stage unrelated changes from other members or existing worktree noise.
- [ ] For business-code implementation beyond Trellis tasks, Agent skills, or collaboration docs, switch to a new branch before editing. Recommended branch: `eir/edge-atlas`.
- [ ] Keep `main` for small Trellis/docs coordination updates unless the user explicitly asks for direct implementation there.
- [ ] After a large update or completed milestone, push the committed branch to the configured remote so collaborators can pull it.
- [ ] Before push, run the relevant validation commands for the files changed. If validation is blocked by board hardware, driver state, or missing assets, document the blocker in the status update.
- [ ] Never force-push unless the user explicitly asks for it and the branch policy is clear.

## Rollback Points

- Keep video-file source working while debugging camera.
- Keep debug/mock runner working while adding ACL/OM runner.
- Keep outbox disabled only behind explicit config; default must protect against upload failure.
- Revert contract-related changes unless docs and OpenAPI are updated together.
