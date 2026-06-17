# 成员1：Atlas 开发板与边缘推理实施计划

## Phase 0: Board Facts

- [ ] Ask user to collect Atlas board facts: board model, OS, CANN version, Python version, camera type, network reachability.
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
- [ ] Search for existing `edge-app`, `camera`, `model-deploy`, upload helpers, or sample payloads before creating new code.

## Phase 2: Skeleton and Config

- [ ] Add edge-side directory/package only if missing.
- [ ] Add default config and local example config covering backend URL, camera source, model paths, thresholds, upload paths, key-frame timing, outbox limits, and ACL device ID.
- [ ] Add typed config loading with clear validation errors.
- [ ] Add logging setup with structured fields aligned to engineering standards.

## Phase 3: Frame Input

- [ ] Implement video/camera source abstraction.
- [ ] Support single-frame capture command for hardware smoke test.
- [ ] Support continuous frame iteration with reconnect/backoff.
- [ ] Save raw frames using `raw/{inspectionId}/{frameId}.jpg`.

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
- [ ] Implement payload builder matching `DetectionUploadRequest`.
- [ ] Implement local outbox write-before-upload and ACK marking.
- [ ] Implement backend uploader with retries and idempotency handling.

## Phase 6: Health and Operations

- [ ] Add local health surface reporting camera, model, ACL, performance, outbox, and backend status.
- [ ] Add clear startup and shutdown lifecycle, releasing camera/model/ACL resources.
- [ ] Add board-side runbook for environment checks, model conversion, startup, and common failures.

## Validation Commands

Run commands will be finalized after the edge package structure exists. Expected checks:

```bash
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/task.py current --source
python3 -m pytest edge-app/tests
python3 edge-app/... --config edge-app/config/local.example.yaml --once
python3 edge-app/... --config edge-app/config/local.example.yaml --source demo-video.mp4
curl http://localhost:8000/api/health
```

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
- [ ] After a large update or completed milestone, push the committed branch to the configured remote so collaborators can pull it.
- [ ] Before push, run the relevant validation commands for the files changed. If validation is blocked by board hardware, driver state, or missing assets, document the blocker in the status update.
- [ ] Never force-push unless the user explicitly asks for it and the branch policy is clear.

## Rollback Points

- Keep video-file source working while debugging camera.
- Keep debug/mock runner working while adding ACL/OM runner.
- Keep outbox disabled only behind explicit config; default must protect against upload failure.
- Revert contract-related changes unless docs and OpenAPI are updated together.
