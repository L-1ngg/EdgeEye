from fastapi import APIRouter

from app.models.inspection import Advice, AdviceGenerateRequest
from app.models.responses import ApiResponse
from app.services.inspection_service import current_timestamp, get_service

router = APIRouter()


@router.post("/advice/generate", response_model=ApiResponse[Advice])
def generate_advice(request: AdviceGenerateRequest) -> ApiResponse[Advice]:
    return ApiResponse(data=get_service().generate_advice(request), timestamp=current_timestamp())


@router.get("/faults/{fault_id}/advice", response_model=ApiResponse[Advice])
def get_fault_advice(fault_id: str) -> ApiResponse[Advice]:
    return ApiResponse(data=get_service().get_fault_advice(fault_id), timestamp=current_timestamp())
