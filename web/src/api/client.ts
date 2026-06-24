import type {
  Alarm,
  ApiResponse,
  DataResult,
  Dashboard,
  Device,
  EventItem,
  Fault,
  InspectionListItem,
  PageResult,
  ProcessStatus,
  RepairAdvice,
  ReportExport,
  ReportSummary,
  RealtimeSnapshot,
  SystemOverview
} from "../types/contracts";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const body = (await response.json()) as ApiResponse<T>;
  return body.data;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const responseBody = (await response.json()) as ApiResponse<T>;
  return responseBody.data;
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const responseBody = (await response.json()) as ApiResponse<T>;
  return responseBody.data;
}

async function getPageItems<T>(path: string): Promise<T[]> {
  const page = await getJson<PageResult<T>>(path);
  return page.items;
}

async function getApiData<T>(loader: () => Promise<T>): Promise<DataResult<T>> {
  return { data: await loader(), source: "api" };
}

export async function getDashboard(): Promise<DataResult<Dashboard>> {
  return getApiData(() => getJson<Dashboard>("/dashboard"));
}

export async function getSystemOverview(): Promise<DataResult<SystemOverview>> {
  return getApiData(() => getJson<SystemOverview>("/system/status"));
}

export async function getRealtimeSnapshot(): Promise<DataResult<RealtimeSnapshot>> {
  return getApiData(async () => {
    const inspections = await getPageItems<InspectionListItem>("/inspections?pageSize=1");
    const latestInspection = inspections[0];

    if (!latestInspection) {
      return createNoFrameSnapshot();
    }

    try {
      return await getJson<RealtimeSnapshot>(`/inspections/${latestInspection.inspectionId}/latest-result`);
    } catch {
      return createNoFrameSnapshot(latestInspection);
    }
  });
}

export function getCameraStreamUrl(): string {
  return `${API_BASE_URL}/camera/stream.mjpg`;
}

export async function getEvents(): Promise<DataResult<EventItem[]>> {
  return getApiData(() => getPageItems<EventItem>("/events"));
}

export async function getReports(): Promise<DataResult<ReportSummary[]>> {
  return getApiData(() => getPageItems<ReportSummary>("/reports"));
}

export async function getDevices(): Promise<DataResult<Device[]>> {
  return getApiData(() => getPageItems<Device>("/devices"));
}

export async function getFaults(): Promise<DataResult<Fault[]>> {
  return getApiData(() => getPageItems<Fault>("/faults"));
}

export async function getAlarms(): Promise<DataResult<Alarm[]>> {
  return getApiData(() => getPageItems<Alarm>("/alarms"));
}

export async function getFaultAdvice(faultId: string | null | undefined): Promise<DataResult<RepairAdvice | null>> {
  if (!faultId) {
    return { data: null, source: "api" };
  }

  try {
    return { data: await getJson<RepairAdvice>(`/faults/${faultId}/advice`), source: "api" };
  } catch {
    return { data: null, source: "unavailable" };
  }
}

export async function generateAdvice(faultId: string): Promise<RepairAdvice> {
  return postJson<RepairAdvice>("/advice/generate", { faultId });
}

export async function updateFaultStatus(
  faultId: string,
  processStatus: ProcessStatus,
  operator = "admin"
): Promise<Fault> {
  return patchJson<Fault>(`/faults/${faultId}/status`, { processStatus, operator });
}

export async function updateAlarmStatus(
  alarmId: string,
  processStatus: ProcessStatus,
  operator = "admin"
): Promise<Alarm> {
  return patchJson<Alarm>(`/alarms/${alarmId}/status`, { processStatus, operator });
}

export async function exportReportPdf(reportId: string): Promise<ReportExport> {
  return getJson<ReportExport>(`/reports/${reportId}/export?format=pdf`);
}

function createNoFrameSnapshot(inspection?: InspectionListItem): RealtimeSnapshot {
  return {
    inspectionId: inspection?.inspectionId ?? "暂无巡检",
    inspectionStatus: inspection?.status ?? "pending",
    resultStatus: "no_frame",
    frameId: null,
    frameSeq: null,
    timestamp: null,
    receivedAt: null,
    staleAfterMs: null,
    isKeyFrame: false,
    uploadReason: "system_event",
    eventKey: null,
    eventStatus: null,
    sampleWindow: null,
    imageUrl: null,
    annotatedImageUrl: null,
    imageWidth: 640,
    imageHeight: 480,
    detections: [],
    performance: {
      latencyMs: 0,
      fps: 0,
      cpuUsage: 0,
      memoryUsage: 0,
      npuUsage: null
    },
    faults: []
  };
}
