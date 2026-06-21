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

## Scenario: Local Smoke Baseline Artifacts

### 1. Scope / Trigger

- Trigger: teammate-provided sample images are used to establish an ONNX
  baseline for later OM/ACL comparison.
- Applies before ATC conversion and before final Atlas ACL inference code is
  available.

### 2. Signatures

- Ignored sample/image output root:
  `model-deploy/artifacts/<model-or-version>-test-images/`.
- Tracked baseline file:
  `model-deploy/expected-output-v1.json`.
- Smoke command stays the adapter command:
  `python3 model-deploy/edge_onnx_bridge.py --image <sample> --payload-output <payload>`.

### 3. Contracts

- Raw teammate images, generated annotated images, and generated payload JSON
  are local artifacts and must stay under `model-deploy/artifacts/`, which is
  ignored by Git.
- `expected-output-v1.json` is tracked and stores stable comparison metadata:
  model version, preprocess/classes versions, thresholds, sample-relative image
  paths, image dimensions, expected class mapping, bbox, and confidence ranges.
- Accuracy is not a pass/fail condition for temporary low-epoch models; payload
  shape, class mapping, bbox bounds, and backend request-model validation are.

### 4. Validation & Error Matrix

- Sample image cannot be decoded -> fail the smoke command before writing the
  baseline.
- Generated payload fails `DetectionUploadRequest` validation -> do not update
  `expected-output-v1.json`.
- Generated detections drift outside confidence range or bbox baseline without
  an intentional model/config change -> investigate before accepting the
  baseline change.
- Artifact path appears in `git ls-files --others --exclude-standard` -> fix
  `.gitignore` or move the artifact before commit.

### 5. Good/Base/Bad Cases

- Good: five raw images and generated payloads stay ignored; the tracked
  expected-output file explains what the later OM/ACL run should match.
- Base: some samples produce `detections: []`; this is valid for a smoke
  baseline when the payload still validates.
- Bad: committing teammate raw images or generated annotated images to Git.

### 6. Tests Required

- Run `python3 -m json.tool model-deploy/expected-output-v1.json`.
- Run ONNX smoke over the sample set and generate payloads.
- Instantiate backend `DetectionUploadRequest` for every generated payload.
- Compare generated payload image sizes, class mapping, bbox, and confidence
  ranges against `expected-output-v1.json`.
- Confirm sample artifacts are ignored by Git with `git check-ignore -v`.

### 7. Wrong vs Correct

#### Wrong

```text
model-deploy/artifacts/transformer-v1-test-images/raw/transformer-v1-001.jpg
model-deploy/artifacts/transformer-v1-test-images/payloads/transformer-v1-001.json
```

Adding these generated artifacts to Git makes the repository carry local test
data and unstable payload timestamps.

#### Correct

```text
model-deploy/expected-output-v1.json
```

Track only the stable baseline metadata; keep raw images, annotated images, and
generated payloads ignored under `model-deploy/artifacts/`.
