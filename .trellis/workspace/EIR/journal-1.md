# Journal - EIR (Part 1)

> AI development session journal
> Started: 2026-06-17

---

## 2026-06-21 - ONNX model bridge scaffold

- Organized local artifacts so large model/data files stay out of Git:
  `models/artifacts/detector-transformer-v1.onnx` and
  `dataset/artifacts/transformer-roboflow-v2-yolov8.zip`.
- Added the model-deploy scaffold committed by the user:
  `edge_onnx_bridge.py`, `classes-v1.json`, `label.names`, and
  `preprocess-v1.json`.
- Current model is a one-class YOLO detect ONNX model for `transformer` only.
  It maps to `deviceType: transformer` and `faultType: null`, so it can drive
  device detection display but not fault/alarm creation.
- Verified the bridge with a dataset sample image, generated an EdgeEye
  detection upload payload, and validated that payload with the backend
  `DetectionUploadRequest` model.
- Next handoff risk: training teammate must provide final class order,
  preprocess/postprocess parameters, test samples, and fault-class mappings
  before Atlas OM/ACL deployment can represent real fault events.

## 2026-06-22 - Remote training handoff review

- Aborted the interrupted rebase, backed up the local handoff commit as
  `backup/insulator-handoff-ff912dc`, then reset `main` to `origin/main` so the
  review used the latest remote training work.
- Remote already contains the training workflow, archived training Trellis
  tasks, and the authoritative insulator domain-r1 report under `dataset/docs/`.
  Avoided duplicating that report under `docs/`.
- Local ignored artifacts contain the insulator domain-r1 ONNX/PT/delivery tar;
  ONNX/PT hashes match the remote report. The useful remaining EIR work is
  Atlas-side ATC/OM/ACL handoff metadata and documentation.
- Added `model-deploy/*edgeeye-insulator-v1*` metadata and documented the next
  ATC command, but did not run ATC or inference pending user confirmation.

## 2026-06-22 - Insulator OM conversion smoke

- Ran ATC for the insulator domain-r1 ONNX on the 310B4 board. The first
  sandboxed attempt failed on system/device permissions; rerunning outside the
  sandbox succeeded.
- Generated ignored OM artifact:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om`
  with SHA-256
  `649934ee37b723e670773e551e169407b4057173117fc178813ea84998022d0c`.
- `atc --mode=6` confirmed `soc_version=Ascend310B4`, toolkit
  `7.0.0.5.242`, memory size `24779264 B`, and weight size `22340096 B`.
- Minimal pyACL smoke loaded the OM and executed one zero input: input
  `images [1,3,640,640]`, output `[1,6,8400]`, about `26.659 ms`.
- Remaining model validation gap: expected-output fixture images live under
  ignored `dataset/processed/...` paths and are absent, so numerical output
  comparison is still pending.

## 2026-06-22 - Camera sample to OM bridge

- Added `model-deploy/edge_acl_om_bridge.py`, which reuses the ONNX bridge
  preprocess/postprocess helpers but executes the insulator OM through pyACL.
- Integrated the backend camera bridge with an `edge_model` service: sampled
  frames are saved raw, sent through the ACL bridge, annotated under
  `/uploads/annotated/...`, then uploaded through the existing
  `DetectionUploadRequest` path. Model failures degrade to empty detections and
  do not stop the MJPEG stream.
- Fixed two board-specific integration issues discovered during live startup:
  `uv run` shadows `python3` with `backend/.venv/bin/python3` lacking
  `cv2/numpy`, so the model subprocess resolves to the board system Python;
  raw/annotated paths are passed to the bridge as absolute paths.
- Verified direct ACL/OM smoke on a real camera sample:
  `640x480`, `26.294 ms`, `detections=[]` for the current non-insulator scene.
- Verified live backend integration: latest result for
  `inspection-20260622-0010` includes both raw and annotated URLs and model
  latency. Backend tests passed with `23 passed, 1 warning`.
- Started backend on `0.0.0.0:8000` and frontend on
  `http://192.168.137.2:5173/` for user inspection.
