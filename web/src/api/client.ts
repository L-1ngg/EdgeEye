import {
  mockAdvice,
  mockDashboard,
  mockEvents,
  mockRealtimeSnapshot,
  mockReports,
  mockSystemOverview
} from "../data/mockData";
import type {
  ApiResponse,
  Dashboard,
  EventItem,
  InspectionListItem,
  PageResult,
  RepairAdvice,
  ReportSummary,
  RealtimeSnapshot,
  SystemOverview
} from "../types/contracts";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const body = (await response.json()) as ApiResponse<T>;
  return body.data;
}

async function getPageItems<T>(path: string): Promise<T[]> {
  const page = await getJson<PageResult<T>>(path);
  return page.items;
}

export async function getDashboard(): Promise<Dashboard> {
  try {
    return await getJson<Dashboard>("/dashboard");
  } catch {
    return mockDashboard;
  }
}

export async function getSystemOverview(): Promise<SystemOverview> {
  try {
    return await getJson<SystemOverview>("/system/status");
  } catch {
    return mockSystemOverview;
  }
}

export async function getRealtimeSnapshot(): Promise<RealtimeSnapshot> {
  try {
    const inspections = await getPageItems<InspectionListItem>("/inspections?pageSize=1");
    const inspectionId = inspections[0]?.inspectionId ?? mockRealtimeSnapshot.inspectionId;
    return await getJson<RealtimeSnapshot>(`/inspections/${inspectionId}/latest-result`);
  } catch {
    return mockRealtimeSnapshot;
  }
}

export async function getEvents(): Promise<EventItem[]> {
  try {
    return await getPageItems<EventItem>("/events");
  } catch {
    return mockEvents;
  }
}

export async function getReports(): Promise<ReportSummary[]> {
  try {
    return await getPageItems<ReportSummary>("/reports");
  } catch {
    return mockReports;
  }
}

export async function getAdvice(faultId: string | null | undefined): Promise<RepairAdvice> {
  if (!faultId) {
    return mockAdvice;
  }

  try {
    return await getJson<RepairAdvice>(`/faults/${faultId}/advice`);
  } catch {
    try {
      const response = await fetch(`${API_BASE_URL}/advice/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ faultId })
      });
      if (!response.ok) {
        return mockAdvice;
      }
      const body = (await response.json()) as ApiResponse<RepairAdvice>;
      return body.data;
    } catch {
      return mockAdvice;
    }
  }
}
