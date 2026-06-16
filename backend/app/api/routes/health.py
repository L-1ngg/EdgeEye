from fastapi import APIRouter

from app.core.config import settings
from app.models.responses import ApiResponse
from app.models.system import HealthStatus
from app.services.demo_data import current_timestamp

router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthStatus])
def get_health() -> ApiResponse[HealthStatus]:
    return ApiResponse(
        data=HealthStatus(status="online", version=settings.app_version),
        timestamp=current_timestamp(),
    )
