import {
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
  return mockRealtimeSnapshot;
}

export async function getEvents(): Promise<EventItem[]> {
  return mockEvents;
}

export async function getReports(): Promise<ReportSummary[]> {
  return mockReports;
}
