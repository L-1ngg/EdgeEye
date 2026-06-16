import { useEffect, useMemo, useState } from "react";

import { getAdvice, getDashboard, getEvents, getRealtimeSnapshot, getReports, getSystemOverview } from "./api/client";
import { mockAdvice, mockDashboard, mockEvents, mockRealtimeSnapshot, mockReports, mockSystemOverview } from "./data/mockData";
import { DashboardPage } from "./pages/DashboardPage";
import { FaultCenterPage } from "./pages/FaultCenterPage";
import { RealtimePage } from "./pages/RealtimePage";
import { ReportsPage } from "./pages/ReportsPage";
import type { Dashboard, EventItem, ReportSummary, RealtimeSnapshot, SystemOverview } from "./types/contracts";

type ViewKey = "dashboard" | "realtime" | "faults" | "reports";

const navItems: Array<{ key: ViewKey; label: string }> = [
  { key: "dashboard", label: "Dashboard" },
  { key: "realtime", label: "实时巡检" },
  { key: "faults", label: "故障中心" },
  { key: "reports", label: "报告中心" }
];

export function App() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard>(mockDashboard);
  const [system, setSystem] = useState<SystemOverview>(mockSystemOverview);
  const [snapshot, setSnapshot] = useState<RealtimeSnapshot>(mockRealtimeSnapshot);
  const [events, setEvents] = useState<EventItem[]>(mockEvents);
  const [advice, setAdvice] = useState(mockAdvice);
  const [reports, setReports] = useState<ReportSummary[]>(mockReports);
  const [apiMode, setApiMode] = useState<"api" | "mock">("mock");

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      const [dashboardData, systemData, snapshotData, eventData, reportData] = await Promise.all([
        getDashboard(),
        getSystemOverview(),
        getRealtimeSnapshot(),
        getEvents(),
        getReports()
      ]);
      const adviceData = await getAdvice(eventData[0]?.faultId);

      if (cancelled) {
        return;
      }

      setDashboard(dashboardData);
      setSystem(systemData);
      setSnapshot(snapshotData);
      setEvents(eventData);
      setAdvice(adviceData);
      setReports(reportData);
      setApiMode(dashboardData === mockDashboard ? "mock" : "api");
    }

    void loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  const page = useMemo(() => {
    switch (activeView) {
      case "dashboard":
        return <DashboardPage dashboard={dashboard} system={system} />;
      case "realtime":
        return <RealtimePage snapshot={snapshot} />;
      case "faults":
        return <FaultCenterPage advice={advice} events={events} />;
      case "reports":
        return <ReportsPage reports={reports} />;
      default:
        return <DashboardPage dashboard={dashboard} system={system} />;
    }
  }, [activeView, advice, dashboard, events, reports, snapshot, system]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span>EdgeEye</span>
          <strong>巡检系统</strong>
        </div>
        <nav className="nav-list" aria-label="主导航">
          {navItems.map((item) => (
            <button
              className={item.key === activeView ? "nav-item nav-item--active" : "nav-item"}
              key={item.key}
              onClick={() => setActiveView(item.key)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Member 4 + Member 5</span>
            <h1>{navItems.find((item) => item.key === activeView)?.label}</h1>
          </div>
          <div className="api-mode">{apiMode === "api" ? "API 已连接" : "Mock 数据"}</div>
        </header>
        {page}
      </section>
    </main>
  );
}
