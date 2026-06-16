from typing import Literal

from fastapi import APIRouter

from app.models.inspection import PageResult, ReportDetail, ReportExport, ReportListItem
from app.models.responses import ApiResponse
from app.services.inspection_service import current_timestamp, get_service

router = APIRouter()


@router.get("/reports", response_model=ApiResponse[PageResult[ReportListItem]])
def list_reports(
    page: int = 1,
    pageSize: int = 20,
    inspectionId: str | None = None,
) -> ApiResponse[PageResult[ReportListItem]]:
    return ApiResponse(
        data=get_service().list_reports(page=page, page_size=pageSize, inspection_id=inspectionId),
        timestamp=current_timestamp(),
    )


@router.get("/reports/{report_id}", response_model=ApiResponse[ReportDetail])
def get_report(report_id: str) -> ApiResponse[ReportDetail]:
    return ApiResponse(data=get_service().get_report(report_id), timestamp=current_timestamp())


@router.get("/reports/{report_id}/export", response_model=ApiResponse[ReportExport])
def export_report(
    report_id: str,
    format: Literal["html", "pdf"] = "html",
) -> ApiResponse[ReportExport]:
    return ApiResponse(data=get_service().export_report(report_id, format), timestamp=current_timestamp())
