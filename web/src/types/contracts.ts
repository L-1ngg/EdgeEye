export type SystemStatus = "online" | "offline" | "degraded" | "error" | "unknown";
export type DataFreshness = "fresh" | "stale" | "offline";
export type PageState = "loading" | "ready" | "empty" | "stale" | "partial_error" | "error";
export type RiskLevel = "none" | "low" | "medium" | "high" | "critical";
export type AlarmLevel = "info" | "warning" | "critical";
export type ProcessStatus = "pending" | "processing" | "resolved" | "ignored";
export type AdviceStatus = "none" | "generating" | "ready" | "fallback" | "failed";
export type ReportStatus = "pending" | "generating" | "ready" | "failed";
export type ReportFormat = "html" | "pdf";
export type ExportStatus = "ready" | "generating" | "failed";
export type ResultStatus = "ready" | "processing" | "stale" | "no_frame" | "failed";
export type InspectionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type EventStatus = "new" | "ongoing" | "resolved";
export type DeviceType = "meter" | "insulator" | "transformer" | "switchgear" | "circuit_breaker" | "unknown";
export type Priority = "P0" | "P1" | "P2" | "P3";
export type DataSource = "api" | "unavailable";

export interface ApiResponse<T> {
  success: true;
  data: T;
  message: string;
  timestamp: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DataResult<T> {
  data: T;
  source: DataSource;
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
  npuUsage: number | null;
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
  idempotencyKey?: string;
  inspectionId: string;
  inspectionStatus: InspectionStatus;
  resultStatus: ResultStatus;
  frameId: string | null;
  frameSeq: number | null;
  timestamp: string | null;
  receivedAt?: string | null;
  staleAfterMs?: number | null;
  isKeyFrame: boolean;
  uploadReason: string;
  eventKey?: string | null;
  eventStatus?: EventStatus | null;
  sampleWindow?: {
    startedAt: string;
    endedAt: string;
    frameCount: number;
  } | null;
  imageUrl?: string | null;
  annotatedImageUrl?: string | null;
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
    npuUsage: number | null;
  };
  faults?: unknown[];
}

export interface EventItem {
  eventId: string;
  eventType: "fault" | "alarm" | "system_exception";
  inspectionId: string;
  deviceId: string;
  deviceName: string;
  faultId: string;
  alarmId: string | null;
  faultType: string;
  riskLevel: RiskLevel;
  alarmLevel: AlarmLevel | null;
  processStatus: ProcessStatus;
  title: string;
  summary: string;
  occurrenceCount: number;
  firstOccurredAt: string;
  lastOccurredAt: string;
  latestFrameId: string;
  latestImageUrl: string;
  adviceStatus: AdviceStatus;
  lastHandledBy?: string | null;
  lastHandledAt?: string | null;
  lastHandleNote?: string | null;
}

export interface Device {
  deviceId: string;
  deviceName: string;
  deviceType: DeviceType;
  location: string;
  status: SystemStatus;
  createdAt: string;
  updatedAt: string;
}

export interface Fault {
  faultId: string;
  inspectionId: string;
  deviceId: string;
  deviceType: DeviceType;
  faultType: string;
  confidence: number;
  riskLevel: RiskLevel;
  alarmRequired: boolean;
  alarmLevel: AlarmLevel;
  priority: Priority;
  processStatus: ProcessStatus;
  eventKey: string;
  eventStatus: EventStatus;
  firstSeenAt: string;
  lastSeenAt: string;
  occurrenceCount: number;
  lastConfidence: number;
  maxConfidence: number;
  bestFrameId: string;
  bestImageUrl: string;
  bestAnnotatedImageUrl: string | null;
  location: string | null;
  createdAt: string;
  lastHandledBy: string | null;
  lastHandledAt: string | null;
  lastHandleNote: string | null;
}

export interface Alarm {
  alarmId: string;
  faultId: string;
  deviceId: string;
  alarmLevel: AlarmLevel;
  riskLevel: RiskLevel;
  message: string;
  processStatus: ProcessStatus;
  dedupKey: string;
  firstTriggeredAt: string;
  lastTriggeredAt: string;
  suppressedCount: number;
  reopenCount: number;
  createdAt: string;
  lastHandledBy: string | null;
  lastHandledAt: string | null;
  lastHandleNote: string | null;
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
  adviceStatus: AdviceStatus;
  createdAt: string;
}

export interface ReportSummary {
  reportId: string;
  inspectionId: string;
  title: string;
  reportStatus: ReportStatus;
  format: ReportFormat;
  createdAt: string;
  url: string;
}

export interface ReportExport {
  format: ReportFormat;
  exportStatus: ExportStatus;
  downloadUrl: string | null;
  fileName: string | null;
  generatedAt: string | null;
  expiresAt: string | null;
}

export interface InspectionListItem {
  inspectionId: string;
  deviceId: string;
  deviceName: string;
  status: InspectionStatus;
  startedAt: string;
  endedAt: string | null;
  faultCount: number;
  alarmCount: number;
}
