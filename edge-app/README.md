# EdgeEye Edge App

This directory contains the edge-side camera bridge for early integration.

The current bridge does not run a vision model. It captures USB camera frames,
saves them under the backend static uploads directory, and uploads an empty
`detections` list to the existing `POST /api/detection/results` contract so the
frontend realtime page can display live camera frames.

## Run

Start the backend first from `backend/`, then run this from the repository root:

```bash
PYTHONPATH=edge-app python3 -m edge_app.live_camera --config edge-app/config/local.example.json
```

Open the frontend realtime page. The script starts a new `atlas` inspection and
uploads one `periodic_sample` frame per second by default.

For a one-frame smoke test:

```bash
PYTHONPATH=edge-app python3 -m edge_app.live_camera --config edge-app/config/local.example.json --once
```

If you already have an inspection ID and want to reuse it:

```bash
PYTHONPATH=edge-app python3 -m edge_app.live_camera \
  --backend-url http://localhost:8000/api \
  --inspection-id inspection-20260618-0001 \
  --source /dev/video0
```

## Important Paths

- `uploadsDir` must point to the same directory that the backend serves at
  `/uploads`. With the local backend command, this is usually `backend/uploads`.
- Frames are saved as `raw/{inspectionId}/{frameId}.jpg`.
- Failed upload payloads are saved under `edge-app/outbox/`.

## Capture Backends

`captureBackend` can be:

- `auto`: try OpenCV first, then ffmpeg, then V4L2.
- `ffmpeg`: use `ffmpeg -f v4l2`; this is currently the best default on the board.
- `v4l2`: use `v4l2-ctl`; this is a fallback when ffmpeg is unavailable.
- `opencv`: use `cv2.VideoCapture`.

The current board has confirmed V4L2 capture on `/dev/video0`. OpenCV direct
camera open has been unreliable, while ffmpeg is faster than one-shot
`v4l2-ctl`, so the example config uses `ffmpeg`.
The bridge does not change the V4L2 format by default because doing so can fail
when the device is already streaming. Use `--set-v4l2-format` only when the
camera is idle and you need to force MJPG width/height.

## Model Status

The backend does not host the YOLO/Atlas vision model. It exposes API endpoints
for inspection lifecycle, detection upload, latest result display, faults,
alarms, advice, and reports. The vision model belongs in the edge app and should
later populate the `detections` list without changing the existing backend
upload route.
