from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.common import (
    AlarmLevel,
    DataFreshness,
    FaultType,
    PageState,
    ProcessStatus,
    RiskLevel,
)


class HighRiskAlarm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alarmId: str
    faultId: str
    inspectionId: str
    deviceId: str
    deviceName: str
    faultType: FaultType
    riskLevel: RiskLevel
    alarmLevel: AlarmLevel
    processStatus: ProcessStatus
    createdAt: datetime


class Dashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceCount: int
    inspectionCount: int
    faultCount: int
    alarmCount: int
    criticalAlarmCount: int
    activeInspectionCount: int
    unresolvedFaultCount: int
    unresolvedAlarmCount: int
    dataFreshness: DataFreshness
    pageState: PageState
    latestInspectionAt: datetime | None = None
    latestHighRiskAlarm: HighRiskAlarm | None = None
