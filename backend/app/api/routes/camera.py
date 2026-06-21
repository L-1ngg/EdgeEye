from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.errors import ApiException
from app.services.camera_bridge import MJPEG_BOUNDARY, CameraCaptureError, camera_bridge_service

router = APIRouter()


@router.get("/camera/stream.mjpg")
def stream_camera() -> StreamingResponse:
    try:
        camera_bridge_service.ensure_stream_available()
    except CameraCaptureError as exc:
        raise ApiException(
            "CAMERA_STREAM_UNAVAILABLE",
            str(exc),
            status_code=503,
        ) from exc
    return StreamingResponse(
        camera_bridge_service.iter_mjpeg_stream(),
        media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
        headers={"Cache-Control": "no-store"},
    )
