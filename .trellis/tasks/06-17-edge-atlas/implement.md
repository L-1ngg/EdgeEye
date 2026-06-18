# 成员1：Atlas 开发板与边缘推理实施计划

## Phase 0: Board Facts

- [x] Ask user to collect Atlas board facts: board model, OS, CANN version, Python version, camera type, network reachability.
- [x] Re-check USB camera after repository update: `/dev/video0` is present and V4L2 can capture MJPG `640x480` test frame.
- [x] Resolve or route around current OpenCV `VideoCapture('/dev/video0', cv2.CAP_V4L2)` open failure before relying on OpenCV for continuous capture.
- [ ] Ask user to confirm model assets: ONNX/OM path, `classes.json`, `label.names`, input size, confidence threshold, IoU threshold.
- [ ] Ask user to confirm backend base URL reachable from board.

## Phase 1: Repository Inspection Before Code

- [ ] Load `trellis-before-dev` before any business-code edit.
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
- [x] Add typed config loading with clear validation errors.
- [x] Add logging setup with structured fields aligned to engineering standards.

## Phase 3: Frame Input

- [x] Implement video/camera source abstraction for ffmpeg and V4L2 capture.
- [x] Support single-frame capture command for hardware smoke test.
- [x] Support continuous frame iteration with retry logging.
- [x] Save raw frames using `raw/{inspectionId}/{frameId}.jpg`.

## Phase 4: Model Runner and Postprocess

- [ ] Implement a common runner interface.
- [ ] Implement debug/mock runner first if Atlas runtime cannot be verified in this environment.
- [ ] Implement ACL/OM runner on board once user confirms CANN/ACL availability.
- [ ] Implement preprocessing: BGR to RGB, resize, normalize, HWC to CHW, batch dimension.
- [ ] Implement YOLO output decoding, confidence filter, coordinate scaling, NMS, and class mapping.
- [ ] Validate bbox and enum output before upload.

## Phase 5: Key Frames, Annotation, Upload

- [ ] Implement annotation writer and save `annotated/{inspectionId}/{frameId}.jpg`.
- [ ] Implement key-frame selector for periodic, started, updated, resolved, manual, and system-event reasons.
- [x] Implement payload builder matching `DetectionUploadRequest` with empty `detections` for no-model realtime display inside backend service code.
- [x] Implement local outbox save on upload failure.
- [ ] Implement backend uploader with retries and idempotency handling.

## Phase 6: Health and Operations

- [x] Add frontend realtime polling through the existing latest-result API path.
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
- The frontend polls latest-result every 1 second after login, so users only start backend and frontend.

Board-side validation commands will be provided to the user step by step and adjusted from real outputs.

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
