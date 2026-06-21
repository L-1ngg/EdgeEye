# Detection Upload Adapters

Edge-side model adapters are allowed to live outside `backend/`, but their
output must preserve the backend upload contract. This spec covers tools such
as `model-deploy/edge_onnx_bridge.py` and any future Atlas OM/ACL adapter that
submits detection results to `POST /api/detection/results`.

## Scenario: ONNX / Edge Detection Upload Adapter

### 1. Scope / Trigger

- Trigger: an external command produces model detections and submits or prints
  a backend `DetectionUploadRequest` payload.
- Applies to local ONNX debugging, future OM/ACL inference, and any temporary
  image-based detection bridge used before the final edge process exists.
- Does not apply to the built-in no-model camera bridge, which is documented in
  `directory-structure.md`.

### 2. Signatures

- Local command:

```bash
python3 model-deploy/edge_onnx_bridge.py --image /path/to/image.jpg
```

- Optional direct upload:

```bash
python3 model-deploy/edge_onnx_bridge.py \
  --image /path/to/image.jpg \
  --api-base http://localhost:8000/api \
  --start-inspection
```

- Required local config files:
  - `model-deploy/classes-v1.json`
  - `model-deploy/label.names`
  - `model-deploy/preprocess-v1.json`
- Default ignored model path:
  - `models/artifacts/detector-transformer-v1.onnx`

### 3. Contracts

- The adapter must output the existing JSON upload shape for
  `POST /api/detection/results`; do not add fields without updating
  `docs/contracts.md` and `docs/openapi.yaml`.
- Each detection must include:
  - `category: string`
  - `deviceType: DeviceType | null`
  - `faultType: FaultType | null`
  - `confidence: number` in `[0, 1]`
  - `bbox: [x1, y1, x2, y2]` in original image pixels
- `classes-v1.json` is the source of truth for class-to-contract mapping.
  Adapters must not infer `deviceType` or `faultType` from raw strings at
  upload time.
- Empty model results must be represented as `detections: []`.
- `imageUrl` and `annotatedImageUrl` must point to backend-visible paths when
  direct upload is used. The adapter may print payloads without uploading while
  images are not yet hosted.

### 4. Validation & Error Matrix

- Missing ONNX/model file -> fail before building payload.
- Missing or invalid class/preprocess JSON -> fail before inference.
- Unknown class id -> map to `category: "<id>"`, `deviceType: "unknown"`,
  and `faultType: null` only as a temporary debug fallback.
- Bbox outside image bounds -> clamp or reject before upload; backend will
  reject invalid boxes with validation error.
- Backend unavailable -> direct upload command exits with a clear HTTP/URL
  error. The final edge process must persist outbox entries instead of dropping
  payloads.

### 5. Good/Base/Bad Cases

- Good: model outputs are converted into EdgeEye `Detection` objects using
  explicit class mappings, original-image pixel boxes, and configurable
  thresholds.
- Base: a one-class `transformer` model maps to `deviceType: transformer` and
  `faultType: null`; this can drive display without creating faults.
- Bad: treating a device-only class as a fault class to force alarms.

### 6. Tests Required

- Syntax and config smoke:
  - `python3 -m py_compile model-deploy/edge_onnx_bridge.py`
  - `python3 -m json.tool model-deploy/classes-v1.json`
  - `python3 -m json.tool model-deploy/preprocess-v1.json`
- Inference smoke with a known sample image should produce a payload file.
- Backend contract smoke should instantiate `DetectionUploadRequest` from the
  generated payload and assert no validation error.
- Direct API smoke, when backend is running, should assert upload success or
  documented idempotent duplicate behavior.

### 7. Wrong vs Correct

#### Wrong

```json
{
  "category": "transformer",
  "deviceType": null,
  "faultType": "surface_damage"
}
```

This invents a fault from a device-only model class.

#### Correct

```json
{
  "category": "transformer",
  "deviceType": "transformer",
  "faultType": null
}
```

This preserves the current model's actual capability and lets the backend store
device detections without creating false fault events.
