from fastapi import APIRouter

from app.models.inspection import (
    DetectionUploadRequest,
    DetectionUploadResult,
    FailInspectionRequest,
    FinishInspectionRequest,
    InspectionListItem,
    InspectionStatusResult,
    LatestInspectionResult,
    PageResult,
    StartInspectionRequest,
)
from app.models.responses import ApiResponse
from app.services.inspection_service import current_timestamp, get_service

router = APIRouter()


@router.post("/inspection/start", response_model=ApiResponse[InspectionStatusResult])
def start_inspection(request: StartInspectionRequest) -> ApiResponse[InspectionStatusResult]:
    return ApiResponse(data=get_service().start_inspection(request), timestamp=current_timestamp())


@router.get("/inspections", response_model=ApiResponse[PageResult[InspectionListItem]])
def list_inspections(
    page: int = 1,
    pageSize: int = 20,
    status: str | None = None,
    deviceId: str | None = None,
) -> ApiResponse[PageResult[InspectionListItem]]:
    return ApiResponse(
        data=get_service().list_inspections(
            page=page,
            page_size=pageSize,
            status=status,
            device_id=deviceId,
        ),
        timestamp=current_timestamp(),
    )


@router.post("/inspections/{inspection_id}/finish", response_model=ApiResponse[InspectionStatusResult])
def finish_inspection(
    inspection_id: str,
    request: FinishInspectionRequest,
) -> ApiResponse[InspectionStatusResult]:
    return ApiResponse(data=get_service().finish_inspection(inspection_id, request), timestamp=current_timestamp())


@router.post("/inspections/{inspection_id}/fail", response_model=ApiResponse[InspectionStatusResult])
def fail_inspection(
    inspection_id: str,
    request: FailInspectionRequest,
) -> ApiResponse[InspectionStatusResult]:
    return ApiResponse(data=get_service().fail_inspection(inspection_id, request), timestamp=current_timestamp())


@router.get("/inspections/{inspection_id}/latest-result", response_model=ApiResponse[LatestInspectionResult])
def get_latest_result(inspection_id: str) -> ApiResponse[LatestInspectionResult]:
    return ApiResponse(data=get_service().get_latest_result(inspection_id), timestamp=current_timestamp())


@router.post("/detection/results", response_model=ApiResponse[DetectionUploadResult])
def upload_detection_result(request: DetectionUploadRequest) -> ApiResponse[DetectionUploadResult]:
    return ApiResponse(data=get_service().upload_detection_result(request), timestamp=current_timestamp())
