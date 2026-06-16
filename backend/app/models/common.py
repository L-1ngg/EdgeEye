from typing import Literal

SystemStatus = Literal["online", "offline", "degraded", "error", "unknown"]
DataFreshness = Literal["fresh", "stale", "offline"]
PageState = Literal["loading", "ready", "empty", "stale", "partial_error", "error"]
RiskLevel = Literal["none", "low", "medium", "high", "critical"]
AlarmLevel = Literal["info", "warning", "critical"]
ProcessStatus = Literal["pending", "processing", "resolved", "ignored"]
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
