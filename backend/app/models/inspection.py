from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import (
    AdviceStatus,
    AlarmLevel,
    DeviceType,
    EventStatus,
    EventType,
    ExportStatus,
    FaultType,
    InspectionSource,
    InspectionStatus,
    Priority,
    ProcessStatus,
    ReportFormat,
    ReportStatus,
    ResultStatus,
    RiskLevel,
    SystemStatus,
    UploadReason,
)

ItemT = TypeVar("ItemT")


class PageResult(BaseModel, Generic[ItemT]):
    model_config = ConfigDict(extra="forbid")

    items: list[ItemT]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1)


class Device(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceId: str
    deviceName: str
    deviceType: DeviceType
    location: str
    status: SystemStatus
    createdAt: datetime
    updatedAt: datetime


class StartInspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceId: str
    operator: str
    source: InspectionSource


class FinishInspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endedAt: datetime | None = None
    summary: str | None = None


class FailInspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endedAt: datetime | None = None
    reason: str


class InspectionStatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspectionId: str
    status: InspectionStatus
    endedAt: datetime | None = None


class InspectionListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspectionId: str
    deviceId: str
    deviceName: str
    status: InspectionStatus
    startedAt: datetime
    endedAt: datetime | None = None
    faultCount: int = Field(ge=0)
    alarmCount: int = Field(ge=0)


class Detection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detectionId: str | None = None
    category: str
    deviceType: DeviceType | None = None
    faultType: FaultType | None = None
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[int, int, int, int]
    imageWidth: int | None = Field(default=None, ge=1)
    imageHeight: int | None = Field(default=None, ge=1)


class Performance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latencyMs: float = Field(default=0, ge=0)
    fps: float = Field(default=0, ge=0)
    cpuUsage: float = Field(default=0, ge=0, le=100)
    memoryUsage: float = Field(default=0, ge=0, le=100)
    npuUsage: float = Field(default=0, ge=0, le=100)


class SampleWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startedAt: datetime
    endedAt: datetime
    frameCount: int = Field(ge=1)


class DetectionUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotencyKey: str
    inspectionId: str
    frameId: str
    frameSeq: int | None = Field(default=None, ge=1)
    timestamp: datetime
    receivedAt: datetime | None = None
    deviceId: str | None = None
    isKeyFrame: bool
    uploadReason: UploadReason
    eventKey: str | None = None
    sampleWindow: SampleWindow | None = None
    imageUrl: str
    annotatedImageUrl: str | None = None
    imageWidth: int = Field(ge=1)
    imageHeight: int = Field(ge=1)
    detections: list[Detection]
    performance: Performance


class DetectionUploadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resultId: str
    inspectionId: str
    frameId: str
    accepted: bool
    duplicate: bool
    processedAt: datetime
    inspectionStatus: InspectionStatus
    faultsCreated: int = Field(ge=0)
    faultsUpdated: int = Field(ge=0)
    alarmsCreated: int = Field(ge=0)
    alarmsSuppressed: int = Field(ge=0)
    reportTriggered: bool
    warnings: list[str]


class Fault(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faultId: str
    inspectionId: str
    deviceId: str
    deviceType: DeviceType
    faultType: FaultType
    confidence: float = Field(ge=0, le=1)
    riskLevel: RiskLevel
    alarmRequired: bool
    alarmLevel: AlarmLevel
    priority: Priority
    processStatus: ProcessStatus
    eventKey: str
    eventStatus: EventStatus
    firstSeenAt: datetime
    lastSeenAt: datetime
    occurrenceCount: int = Field(ge=1)
    lastConfidence: float = Field(ge=0, le=1)
    maxConfidence: float = Field(ge=0, le=1)
    bestFrameId: str
    bestImageUrl: str
    bestAnnotatedImageUrl: str | None = None
    location: str | None = None
    createdAt: datetime


class Alarm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alarmId: str
    faultId: str
    deviceId: str
    alarmLevel: AlarmLevel
    riskLevel: RiskLevel
    message: str
    processStatus: ProcessStatus
    dedupKey: str
    firstTriggeredAt: datetime
    lastTriggeredAt: datetime
    suppressedCount: int = Field(ge=0)
    reopenCount: int = Field(default=0, ge=0)
    createdAt: datetime


class LatestInspectionResult(DetectionUploadRequest):
    inspectionStatus: InspectionStatus
    resultStatus: ResultStatus
    staleAfterMs: int = Field(default=3000, ge=0)
    eventStatus: EventStatus | None = None
    faults: list[Fault]


class EventItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: str
    eventType: EventType
    inspectionId: str
    deviceId: str
    deviceName: str
    faultId: str
    alarmId: str | None = None
    faultType: FaultType
    riskLevel: RiskLevel
    alarmLevel: AlarmLevel | None = None
    processStatus: ProcessStatus
    title: str
    summary: str
    occurrenceCount: int = Field(ge=1)
    firstOccurredAt: datetime
    lastOccurredAt: datetime
    latestFrameId: str
    latestImageUrl: str
    adviceStatus: AdviceStatus


class UpdateProcessStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processStatus: ProcessStatus
    operator: str
    note: str | None = None


class AdviceGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faultId: str


class Advice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adviceId: str
    faultId: str
    possibleCauses: list[str]
    riskAnalysis: str
    inspectionSteps: list[str]
    maintenanceSuggestions: list[str]
    safetyNotes: list[str]
    modelName: str
    adviceStatus: AdviceStatus
    createdAt: datetime


class ReportListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reportId: str
    inspectionId: str
    title: str
    reportStatus: ReportStatus
    createdAt: datetime
    format: ReportFormat
    url: str


class ReportExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: ReportFormat
    exportStatus: ExportStatus
    downloadUrl: str | None = None
    fileName: str | None = None
    generatedAt: datetime | None = None
    expiresAt: datetime | None = None


class ReportDetail(ReportListItem):
    summary: str
    device: Device
    faults: list[Fault]
    alarms: list[Alarm]
    advices: list[Advice]
    exports: list[ReportExport]
