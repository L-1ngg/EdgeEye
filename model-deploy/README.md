# Model Deploy Smoke Checks

This directory holds local model deployment helpers and tracked metadata for
EdgeEye edge/model integration. Large model files, sample images, annotated
images, and generated payloads live under `model-deploy/artifacts/` or
`models/artifacts/` and are ignored by Git.

## Transformer V1 ONNX Smoke

Current temporary model contract:

- model: `models/artifacts/detector-transformer-v1.onnx`
- model type: YOLOv8 detect
- classes: one class, `0: transformer`
- input size: `640x640`
- confidence threshold: `0.25`
- NMS IoU threshold: `0.45`
- sample root: `model-deploy/artifacts/transformer-v1-test-images/`

The model was trained for only 3 epochs, so this smoke check verifies that the
pipeline runs and emits the expected payload shape. Detection accuracy is not a
pass/fail criterion.

Run one image:

```bash
python3 model-deploy/edge_onnx_bridge.py \
  --image model-deploy/artifacts/transformer-v1-test-images/raw/transformer-v1-001.jpg \
  --frame-id frame-001 \
  --inspection-id inspection-transformer-v1-smoke \
  --annotated-output model-deploy/artifacts/transformer-v1-test-images/annotated/transformer-v1-001.jpg \
  --payload-output model-deploy/artifacts/transformer-v1-test-images/payloads/transformer-v1-001.json
```

Validate a generated payload against the backend request model:

```bash
backend/.venv/bin/python -c "import json, sys; sys.path.insert(0, 'backend'); from app.models.inspection import DetectionUploadRequest; DetectionUploadRequest(**json.load(open('model-deploy/artifacts/transformer-v1-test-images/payloads/transformer-v1-001.json'))); print('payload validation ok')"
```

Use `model-deploy/expected-output-v1.json` as the ONNX baseline when comparing
future Atlas OM/ACL output. The future comparison should focus on output shape,
class mapping, coordinate range, and payload validity before model accuracy.

## EdgeEye Insulator V1 Domain-R1 Candidate

The stronger insulator-only candidate is delivered as local ignored artifacts:

- delivery package:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw-delivery.tar.gz`
- ONNX for ATC:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.onnx`
- PT checkpoint:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.pt`
- training and validation report:
  `dataset/docs/edgeeye-insulator-v1-domain-r1-report.md`

Tracked deploy metadata for the candidate lives in this directory:

- `classes-edgeeye-insulator-v1.json`
- `label-edgeeye-insulator-v1.names`
- `preprocess-edgeeye-insulator-v1.json`
- `expected-output-edgeeye-insulator-v1.json`

Candidate contract:

- model type: YOLOv8 detect
- classes: `0: insulator_normal`, `1: insulator_surface_damage`
- input: `images [1,3,640,640]`
- output: `output0 [1,6,8400]`
- confidence threshold: `0.25`
- NMS IoU threshold: `0.45`

Convert the ONNX model to an Atlas OM model for the current 310B4 board:

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

The `--output` value omits the suffix; ATC writes
`models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om`.
If the target board changes, replace `--soc_version` with the value confirmed
from `npu-smi info`.

Inspect the converted OM metadata:

```bash
atc --mode=6 \
  --om=models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om
```

Run one image through the Atlas ACL/OM bridge and emit backend-ready detection
JSON:

```bash
python3 model-deploy/edge_acl_om_bridge.py \
  --model models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om \
  --image /path/to/frame.jpg \
  --classes model-deploy/classes-edgeeye-insulator-v1.json \
  --preprocess model-deploy/preprocess-edgeeye-insulator-v1.json \
  --annotated-output /tmp/edgeeye-annotated.jpg \
  --output-shape 1,6,8400
```

The backend camera bridge calls this script for sampled frames when
`EDGEEYE_EDGE_MODEL_ENABLED=true`, parses the JSON output, saves the annotated
image under `/uploads/annotated/...`, and uploads detections through the
existing `POST /api/detection/results` contract.

After OM/ACL inference is available, compare its class mapping, bbox range, and
confidence values against `expected-output-edgeeye-insulator-v1.json`. Use the
fixture tolerances instead of exact floating-point equality.

Current board result from 2026-06-22:

- ATC conversion succeeded on `Ascend310B4`.
- OM path:
  `models/artifacts/edgeeye-insulator-v1-domain-r1-opt30-yolov8s-adamw.om`
- OM SHA-256:
  `649934ee37b723e670773e551e169407b4057173117fc178813ea84998022d0c`
- `atc --mode=6` reports `atc_version=7.0.0.5.242`,
  `memory_size=24779264 B`, and `weight_size=22340096 B`.
- Minimal pyACL execution smoke passed with one zero tensor:
  input `images [1,3,640,640]`, output `[1,6,8400]`, output buffer
  `201600` bytes, single execute about `26.659 ms`.

The expected-output fixture images are under ignored `dataset/processed/...`
paths and are not present in the current checkout, so case-by-case numerical
comparison remains pending.
