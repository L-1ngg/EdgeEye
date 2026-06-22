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
