from fastapi import APIRouter

from app.models.responses import ApiResponse
from app.models.system import SystemOverview
from app.services.demo_data import current_timestamp, get_system_overview

router = APIRouter()


@router.get("/status", response_model=ApiResponse[SystemOverview])
def get_system_status() -> ApiResponse[SystemOverview]:
    return ApiResponse(data=get_system_overview(), timestamp=current_timestamp())
