from datetime import UTC, datetime

from app.models.dashboard import Dashboard, HighRiskAlarm
from app.models.system import AtlasStatus, ModelStatus, SubsystemStatus, SystemOverview


def current_timestamp() -> datetime:
    return datetime.now(UTC)


def get_system_overview() -> SystemOverview:
    now = current_timestamp()
    return SystemOverview(
        camera=SubsystemStatus(
            status="online",
            lastFrameAt=now,
            lastHeartbeatAt=now,
            message="camera stream is healthy",
            degradedReason=None,
        ),
        atlas=AtlasStatus(
            status="online",
            lastHeartbeatAt=now,
            message="edge app is uploading key frames",
            degradedReason=None,
            cpuUsage=42.5,
            memoryUsage=61.2,
            npuUsage=38.4,
        ),
        model=ModelStatus(
            status="online",
            lastHeartbeatAt=now,
            message="model inference is healthy",
            degradedReason=None,
            modelVersion="detector-v1",
            fps=18.5,
            latencyMs=42,
        ),
        backend=SubsystemStatus(
            status="online",
            lastHeartbeatAt=now,
            message="api service is healthy",
            degradedReason=None,
        ),
        updatedAt=now,
        dataFreshness="fresh",
        activeInspectionCount=1,
        unresolvedFaultCount=1,
        unresolvedAlarmCount=1,
    )


def get_dashboard() -> Dashboard:
    now = current_timestamp()
    return Dashboard(
        deviceCount=4,
        inspectionCount=12,
        faultCount=3,
        alarmCount=3,
        criticalAlarmCount=0,
        activeInspectionCount=1,
        unresolvedFaultCount=1,
        unresolvedAlarmCount=1,
        dataFreshness="fresh",
        pageState="ready",
        latestInspectionAt=now,
        latestHighRiskAlarm=HighRiskAlarm(
            alarmId="alarm-000001",
            faultId="fault-000001",
            inspectionId="inspection-20260616-0001",
            deviceId="device-001",
            deviceName="2号线路绝缘子",
            faultType="surface_damage",
            riskLevel="high",
            alarmLevel="warning",
            processStatus="pending",
            createdAt=now,
        ),
    )
