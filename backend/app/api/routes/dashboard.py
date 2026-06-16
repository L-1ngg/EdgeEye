from fastapi import APIRouter

from app.models.dashboard import Dashboard
from app.models.responses import ApiResponse
from app.services.demo_data import current_timestamp, get_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=ApiResponse[Dashboard])
def get_dashboard_summary() -> ApiResponse[Dashboard]:
    return ApiResponse(data=get_dashboard(), timestamp=current_timestamp())
