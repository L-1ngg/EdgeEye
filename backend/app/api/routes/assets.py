from fastapi import APIRouter

from app.models.inspection import (
    Alarm,
    Device,
    EventItem,
    Fault,
    PageResult,
    UpdateProcessStatusRequest,
)
from app.models.responses import ApiResponse
from app.services.inspection_service import current_timestamp, get_service

router = APIRouter()


@router.get("/devices", response_model=ApiResponse[PageResult[Device]])
def list_devices(
    deviceType: str | None = None,
    status: str | None = None,
) -> ApiResponse[PageResult[Device]]:
    return ApiResponse(
        data=get_service().list_devices(device_type=deviceType, status=status),
        timestamp=current_timestamp(),
    )


@router.get("/faults", response_model=ApiResponse[PageResult[Fault]])
def list_faults(
    page: int = 1,
    pageSize: int = 20,
    riskLevel: str | None = None,
    processStatus: str | None = None,
    deviceId: str | None = None,
) -> ApiResponse[PageResult[Fault]]:
    return ApiResponse(
        data=get_service().list_faults(
            page=page,
            page_size=pageSize,
            risk_level=riskLevel,
            process_status=processStatus,
            device_id=deviceId,
        ),
        timestamp=current_timestamp(),
    )


@router.get("/alarms", response_model=ApiResponse[PageResult[Alarm]])
def list_alarms(
    page: int = 1,
    pageSize: int = 20,
    alarmLevel: str | None = None,
    processStatus: str | None = None,
) -> ApiResponse[PageResult[Alarm]]:
    return ApiResponse(
        data=get_service().list_alarms(
            page=page,
            page_size=pageSize,
            alarm_level=alarmLevel,
            process_status=processStatus,
        ),
        timestamp=current_timestamp(),
    )


@router.get("/events", response_model=ApiResponse[PageResult[EventItem]])
def list_events(
    page: int = 1,
    pageSize: int = 20,
    riskLevel: str | None = None,
    processStatus: str | None = None,
    adviceStatus: str | None = None,
) -> ApiResponse[PageResult[EventItem]]:
    return ApiResponse(
        data=get_service().list_events(
            page=page,
            page_size=pageSize,
            risk_level=riskLevel,
            process_status=processStatus,
            advice_status=adviceStatus,
        ),
        timestamp=current_timestamp(),
    )


@router.patch("/faults/{fault_id}/status", response_model=ApiResponse[Fault])
def update_fault_status(
    fault_id: str,
    request: UpdateProcessStatusRequest,
) -> ApiResponse[Fault]:
    return ApiResponse(data=get_service().update_fault_status(fault_id, request), timestamp=current_timestamp())


@router.patch("/alarms/{alarm_id}/status", response_model=ApiResponse[Alarm])
def update_alarm_status(
    alarm_id: str,
    request: UpdateProcessStatusRequest,
) -> ApiResponse[Alarm]:
    return ApiResponse(data=get_service().update_alarm_status(alarm_id, request), timestamp=current_timestamp())
