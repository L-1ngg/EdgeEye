from typing import Literal

SystemStatus = Literal["online", "offline", "degraded", "error", "unknown"]
DataFreshness = Literal["fresh", "stale", "offline"]
PageState = Literal["loading", "ready", "empty", "stale", "partial_error", "error"]
DeviceType = Literal["meter", "insulator", "transformer", "switchgear", "circuit_breaker", "unknown"]
RiskLevel = Literal["none", "low", "medium", "high", "critical"]
AlarmLevel = Literal["info", "warning", "critical"]
ProcessStatus = Literal["pending", "processing", "resolved", "ignored"]
InspectionStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
InspectionSource = Literal["atlas", "web", "mock"]
Priority = Literal["P0", "P1", "P2", "P3"]
UploadReason = Literal[
    "periodic_sample",
    "fault_started",
    "fault_updated",
    "fault_resolved",
    "manual_capture",
    "system_event",
]
ResultStatus = Literal["ready", "processing", "stale", "no_frame", "failed"]
EventStatus = Literal["new", "ongoing", "resolved"]
EventType = Literal["fault", "alarm", "system_exception"]
AdviceStatus = Literal["none", "generating", "ready", "fallback", "failed"]
ReportStatus = Literal["pending", "generating", "ready", "failed"]
ReportFormat = Literal["html", "pdf"]
ExportStatus = Literal["ready", "generating", "failed"]
FaultType = Literal[
    "surface_damage",
    "rust",
    "foreign_object",
    "smoke",
    "fire",
    "person_intrusion",
    "helmet_missing",
    "unknown",
]
