import type {
  Dashboard,
  EventItem,
  RepairAdvice,
  ReportSummary,
  RealtimeSnapshot,
  SystemOverview
} from "../types/contracts";

const now = "2026-06-17T00:00:00+08:00";

export const mockSystemOverview: SystemOverview = {
  camera: {
    status: "online",
    lastFrameAt: now,
    lastHeartbeatAt: now,
    message: "camera stream is healthy",
    degradedReason: null
  },
  atlas: {
    status: "online",
    cpuUsage: 42.5,
    memoryUsage: 61.2,
    npuUsage: 38.4,
    lastHeartbeatAt: now,
    message: "edge app is uploading key frames",
    degradedReason: null
  },
  model: {
    status: "online",
    modelVersion: "detector-v1",
    fps: 18.5,
    latencyMs: 42,
    lastHeartbeatAt: now,
    message: "model inference is healthy",
    degradedReason: null
  },
  backend: {
    status: "online",
    lastHeartbeatAt: now,
    message: "api service is healthy",
    degradedReason: null
  },
  updatedAt: now,
  dataFreshness: "fresh",
  activeInspectionCount: 1,
  unresolvedFaultCount: 1,
  unresolvedAlarmCount: 1
};

export const mockDashboard: Dashboard = {
  deviceCount: 4,
  inspectionCount: 12,
  faultCount: 3,
  alarmCount: 3,
  criticalAlarmCount: 0,
  activeInspectionCount: 1,
  unresolvedFaultCount: 1,
  unresolvedAlarmCount: 1,
  dataFreshness: "fresh",
  pageState: "ready",
  latestInspectionAt: now,
  latestHighRiskAlarm: {
    alarmId: "alarm-000001",
    faultId: "fault-000001",
    inspectionId: "inspection-20260616-0001",
    deviceId: "device-001",
    deviceName: "2号线路绝缘子",
    faultType: "surface_damage",
    riskLevel: "high",
    alarmLevel: "warning",
    processStatus: "pending",
    createdAt: now
  }
};

export const mockRealtimeSnapshot: RealtimeSnapshot = {
  inspectionId: "inspection-20260616-0001",
  inspectionStatus: "running",
  resultStatus: "ready",
  frameId: "frame-000021",
  frameSeq: 21,
  timestamp: now,
  isKeyFrame: true,
  uploadReason: "fault_updated",
  imageWidth: 1280,
  imageHeight: 720,
  detections: [
    {
      detectionId: "detection-000001",
      category: "insulator_defect",
      deviceType: "insulator",
      faultType: "surface_damage",
      confidence: 0.91,
      bbox: [120, 80, 360, 420]
    }
  ],
  performance: {
    latencyMs: 42,
    fps: 18.5,
    cpuUsage: 42.5,
    memoryUsage: 61.2,
    npuUsage: 38.4
  }
};

export const mockEvents: EventItem[] = [
  {
    eventId: "event-000001",
    eventType: "fault",
    inspectionId: "inspection-20260616-0001",
    deviceId: "device-001",
    deviceName: "2号线路绝缘子",
    faultId: "fault-000001",
    alarmId: "alarm-000001",
    faultType: "surface_damage",
    riskLevel: "high",
    alarmLevel: "warning",
    processStatus: "pending",
    title: "绝缘子表面破损",
    summary: "同一故障持续出现 6 次，已保留最佳证据帧。",
    occurrenceCount: 6,
    firstOccurredAt: "2026-06-16T10:00:00+08:00",
    lastOccurredAt: "2026-06-16T10:00:08+08:00",
    latestFrameId: "frame-000021",
    latestImageUrl: "/uploads/annotated/inspection-20260616-0001/frame-000021.jpg",
    adviceStatus: "ready"
  }
];

export const mockAdvice: RepairAdvice = {
  adviceId: "advice-000001",
  faultId: "fault-000001",
  possibleCauses: ["机械冲击", "长期老化"],
  riskAnalysis: "可能降低绝缘性能，需要安排复检。",
  inspectionSteps: ["检查破损范围", "检查是否存在放电痕迹"],
  maintenanceSuggestions: ["安排专业人员复检", "必要时更换绝缘子"],
  safetyNotes: ["操作前确认设备状态", "维修建议需人工审核"],
  modelName: "rule-template",
  createdAt: now
};

export const mockReports: ReportSummary[] = [
  {
    reportId: "report-20260616-0001",
    inspectionId: "inspection-20260616-0001",
    title: "2号线路绝缘子巡检报告",
    status: "ready",
    format: "pdf",
    generatedAt: now,
    downloadUrl: "/reports/report-20260616-0001.pdf"
  },
  {
    reportId: "report-20260616-0002",
    inspectionId: "inspection-20260616-0002",
    title: "变电站例行巡检报告",
    status: "generating",
    format: "pdf",
    generatedAt: null,
    downloadUrl: null
  }
];
