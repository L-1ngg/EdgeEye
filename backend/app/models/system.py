from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.common import DataFreshness, SystemStatus


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SystemStatus
    version: str


class SubsystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SystemStatus
    lastFrameAt: datetime | None = None
    lastHeartbeatAt: datetime | None = None
    message: str | None = None
    degradedReason: str | None = None


class AtlasStatus(SubsystemStatus):
    cpuUsage: float
    memoryUsage: float
    npuUsage: float


class ModelStatus(SubsystemStatus):
    modelVersion: str
    fps: float
    latencyMs: int


class SystemOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera: SubsystemStatus
    atlas: AtlasStatus
    model: ModelStatus
    backend: SubsystemStatus
    updatedAt: datetime
    dataFreshness: DataFreshness
    activeInspectionCount: int
    unresolvedFaultCount: int
    unresolvedAlarmCount: int
