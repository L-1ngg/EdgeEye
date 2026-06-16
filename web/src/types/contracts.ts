export type SystemStatus = "online" | "offline" | "degraded" | "error" | "unknown";
export type DataFreshness = "fresh" | "stale" | "offline";
export type PageState = "loading" | "ready" | "empty" | "stale" | "partial_error" | "error";
export type RiskLevel = "none" | "low" | "medium" | "high" | "critical";
export type AlarmLevel = "info" | "warning" | "critical";
export type ProcessStatus = "pending" | "processing" | "resolved" | "ignored";
export type AdviceStatus = "none" | "generating" | "ready" | "fallback" | "failed";
export type ReportStatus = "pending" | "generating" | "ready" | "failed";

export interface ApiResponse<T> {
  success: true;
  data: T;
  message: string;
  timestamp: string;
}

export interface SubsystemStatus {
  status: SystemStatus;
  lastFrameAt?: string | null;
  lastHeartbeatAt?: string | null;
  message?: string | null;
  degradedReason?: string | null;
}

export interface AtlasStatus extends SubsystemStatus {
  cpuUsage: number;
  memoryUsage: number;
  npuUsage: number;
}

export interface ModelStatus extends SubsystemStatus {
  modelVersion: string;
  fps: number;
  latencyMs: number;
}

export interface SystemOverview {
  camera: SubsystemStatus;
  atlas: AtlasStatus;
  model: ModelStatus;
  backend: SubsystemStatus;
  updatedAt: string;
  dataFreshness: DataFreshness;
  activeInspectionCount: number;
  unresolvedFaultCount: number;
  unresolvedAlarmCount: number;
}

export interface HighRiskAlarm {
  alarmId: string;
  faultId: string;
  inspectionId: string;
  deviceId: string;
  deviceName: string;
  faultType: string;
  riskLevel: RiskLevel;
  alarmLevel: AlarmLevel;
  processStatus: ProcessStatus;
  createdAt: string;
}

export interface Dashboard {
  deviceCount: number;
  inspectionCount: number;
  faultCount: number;
  alarmCount: number;
  criticalAlarmCount: number;
  activeInspectionCount: number;
  unresolvedFaultCount: number;
  unresolvedAlarmCount: number;
  dataFreshness: DataFreshness;
  pageState: PageState;
  latestInspectionAt: string | null;
  latestHighRiskAlarm: HighRiskAlarm | null;
}

export interface RealtimeSnapshot {
  inspectionId: string;
  inspectionStatus: string;
  resultStatus: "ready" | "processing" | "stale" | "no_frame" | "failed";
  frameId: string;
  frameSeq: number;
  timestamp: string;
  isKeyFrame: boolean;
  uploadReason: string;
  imageWidth: number;
  imageHeight: number;
  detections: Array<{
    detectionId: string;
    category: string;
    deviceType: string | null;
    faultType: string | null;
    confidence: number;
    bbox: [number, number, number, number];
  }>;
  performance: {
    latencyMs: number;
    fps: number;
    cpuUsage: number;
    memoryUsage: number;
    npuUsage: number;
  };
}

export interface EventItem {
  eventId: string;
  eventType: "fault" | "alarm" | "system_exception";
  inspectionId: string;
  deviceId: string;
  deviceName: string;
  faultId: string;
  alarmId: string;
  faultType: string;
  riskLevel: RiskLevel;
  alarmLevel: AlarmLevel;
  processStatus: ProcessStatus;
  title: string;
  summary: string;
  occurrenceCount: number;
  firstOccurredAt: string;
  lastOccurredAt: string;
  latestFrameId: string;
  latestImageUrl: string;
  adviceStatus: AdviceStatus;
}

export interface RepairAdvice {
  adviceId: string;
  faultId: string;
  possibleCauses: string[];
  riskAnalysis: string;
  inspectionSteps: string[];
  maintenanceSuggestions: string[];
  safetyNotes: string[];
  modelName: string;
  createdAt: string;
}

export interface ReportSummary {
  reportId: string;
  inspectionId: string;
  title: string;
  status: ReportStatus;
  format: "pdf" | "html" | "docx";
  generatedAt: string | null;
  downloadUrl: string | null;
}
