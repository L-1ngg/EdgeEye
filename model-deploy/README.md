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
