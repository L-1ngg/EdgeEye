import { useEffect, useState } from "react";

import {
  generateAdvice,
  getAlarms,
  getDashboard,
  getDevices,
  getEvents,
  getFaultAdvice,
  getFaults,
  getRealtimeSnapshot,
  getReports,
  getSystemOverview,
  updateAlarmStatus,
  updateFaultStatus
} from "./api/client";
import { clearDemoAdminSession, hasDemoAdminSession } from "./auth/session";
import { Icon, type IconName } from "./components/Icon";
import { AssetsPage } from "./pages/AssetsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FaultCenterPage } from "./pages/FaultCenterPage";
import { LoginPage } from "./pages/LoginPage";
import { RealtimePage } from "./pages/RealtimePage";
import { ReportsPage } from "./pages/ReportsPage";
import { useTheme } from "./theme/useTheme";
import type { Alarm, Dashboard, DataSource, Device, EventItem, Fault, ProcessStatus, RepairAdvice, ReportSummary, RealtimeSnapshot, SystemOverview } from "./types/contracts";

type ViewKey = "dashboard" | "realtime" | "faults" | "reports" | "assets";

interface AppData {
  dashboard: Dashboard;
  system: SystemOverview;
  snapshot: RealtimeSnapshot;
  events: EventItem[];
  adviceByFaultId: Record<string, RepairAdvice | null>;
  reports: ReportSummary[];
  devices: Device[];
  faults: Fault[];
  alarms: Alarm[];
}

const navItems: Array<{ key: ViewKey; label: string; icon: IconName }> = [
  { key: "dashboard", label: "运行总览", icon: "grid" },
  { key: "realtime", label: "实时巡检", icon: "video" },
  { key: "faults", label: "故障中心", icon: "alert-triangle" },
  { key: "reports", label: "报告中心", icon: "file-text" },
  { key: "assets", label: "系统资源", icon: "database" }
];
const defaultView: ViewKey = "dashboard";
const realtimeRefreshMs = 1000;
const operationalDataRefreshMs = 3000;
const viewKeys = new Set<ViewKey>(navItems.map((item) => item.key));

export function App() {
  const { theme, toggleTheme } = useTheme();
  const [isAuthenticated, setIsAuthenticated] = useState(() => hasDemoAdminSession());
  const [activeView, setActiveView] = useState<ViewKey>(() => getViewFromLocation());
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [appData, setAppData] = useState<AppData | null>(null);
  const [adviceLoadingFaultId, setAdviceLoadingFaultId] = useState<string | null>(null);
  const [adviceErrorByFaultId, setAdviceErrorByFaultId] = useState<Record<string, string | null>>({});
  const [dataSources, setDataSources] = useState<Record<ViewKey, DataSource>>({
    dashboard: "unavailable",
    realtime: "unavailable",
    faults: "unavailable",
    reports: "unavailable",
    assets: "unavailable"
  });

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    async function loadData() {
      try {
        const [dashboardResult, systemResult, snapshotResult, eventResult, reportResult, deviceResult, faultResult, alarmResult] = await Promise.all([
          getDashboard(),
          getSystemOverview(),
          getRealtimeSnapshot(),
          getEvents(),
          getReports(),
          getDevices(),
          getFaults(),
          getAlarms()
        ]);
        if (cancelled) {
          return;
        }

        setAppData({
          dashboard: dashboardResult.data,
          system: systemResult.data,
          snapshot: snapshotResult.data,
          events: eventResult.data,
          adviceByFaultId: {},
          reports: reportResult.data,
          devices: deviceResult.data,
          faults: faultResult.data,
          alarms: alarmResult.data
        });
        setDataSources({
          dashboard: "api",
          realtime: "api",
          faults: "api",
          reports: "api",
          assets: "api"
        });
      } catch {
        if (cancelled) {
          return;
        }

        setAppData(createEmptyAppData());
        setDataSources({
          dashboard: "unavailable",
          realtime: "unavailable",
          faults: "unavailable",
          reports: "unavailable",
          assets: "unavailable"
        });
      }
    }

    void loadData();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    async function refreshOperationalData() {
      try {
        const [dashboardResult, systemResult, eventResult, faultResult, alarmResult, reportResult] = await Promise.all([
          getDashboard(),
          getSystemOverview(),
          getEvents(),
          getFaults(),
          getAlarms(),
          getReports()
        ]);

        if (cancelled) {
          return;
        }

        setAppData((currentData) => {
          if (!currentData) {
            return currentData;
          }

          return {
            ...currentData,
            dashboard: dashboardResult.data,
            system: systemResult.data,
            events: eventResult.data,
            faults: faultResult.data,
            alarms: alarmResult.data,
            reports: reportResult.data
          };
        });
        setDataSources((currentSources) => ({
          ...currentSources,
          dashboard: dashboardResult.source,
          faults: eventResult.source === "api" && faultResult.source === "api" && alarmResult.source === "api" ? "api" : "unavailable",
          reports: reportResult.source,
          assets: faultResult.source === "api" && alarmResult.source === "api" ? "api" : "unavailable"
        }));
      } catch {
        if (cancelled) {
          return;
        }

        setDataSources((currentSources) => ({
          ...currentSources,
          dashboard: "unavailable",
          faults: "unavailable",
          reports: "unavailable",
          assets: "unavailable"
        }));
      }
    }

    const intervalId = window.setInterval(() => {
      void refreshOperationalData();
    }, operationalDataRefreshMs);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    async function refreshRealtimeSnapshot() {
      try {
        const snapshotResult = await getRealtimeSnapshot();

        if (cancelled) {
          return;
        }

        setAppData((currentData) => {
          if (!currentData) {
            return currentData;
          }

          return {
            ...currentData,
            snapshot: snapshotResult.data
          };
        });
        setDataSources((currentSources) => ({
          ...currentSources,
          realtime: snapshotResult.source
        }));
      } catch {
        if (cancelled) {
          return;
        }

        setDataSources((currentSources) => ({
          ...currentSources,
          realtime: "unavailable"
        }));
      }
    }

    const intervalId = window.setInterval(() => {
      void refreshRealtimeSnapshot();
    }, realtimeRefreshMs);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [isAuthenticated]);

  useEffect(() => {
    function handleLocationChange() {
      setActiveView(getViewFromLocation());
    }

    window.addEventListener("hashchange", handleLocationChange);
    window.addEventListener("popstate", handleLocationChange);

    return () => {
      window.removeEventListener("hashchange", handleLocationChange);
      window.removeEventListener("popstate", handleLocationChange);
    };
  }, []);

  const page = (() => {
    if (!appData) {
      return <LoadingPage />;
    }

    switch (activeView) {
      case "dashboard":
        return <DashboardPage dashboard={appData.dashboard} dataSource={dataSources.dashboard} system={appData.system} />;
      case "realtime":
        return <RealtimePage dataSource={dataSources.realtime} snapshot={appData.snapshot} />;
      case "faults":
        return (
          <FaultCenterPage
            adviceByFaultId={appData.adviceByFaultId}
            adviceErrorByFaultId={adviceErrorByFaultId}
            adviceLoadingFaultId={adviceLoadingFaultId}
            dataSource={dataSources.faults}
            events={appData.events}
            onGenerateAdvice={handleGenerateAdvice}
            onLoadAdvice={handleLoadAdvice}
            onUpdateStatus={handleUpdateStatus}
          />
        );
      case "reports":
        return <ReportsPage dataSource={dataSources.reports} reports={appData.reports} />;
      case "assets":
        return <AssetsPage alarms={appData.alarms} dataSource={dataSources.assets} devices={appData.devices} faults={appData.faults} />;
      default:
        return <DashboardPage dashboard={appData.dashboard} dataSource={dataSources.dashboard} system={appData.system} />;
    }
  })();

  async function handleUpdateStatus(event: EventItem, processStatus: ProcessStatus) {
    const updatedFault = await updateFaultStatus(event.faultId, processStatus);
    let updatedAlarm: Alarm | null = null;

    if (event.alarmId) {
      updatedAlarm = await updateAlarmStatus(event.alarmId, processStatus);
    }

    setAppData((currentData) => {
      if (!currentData) {
        return currentData;
      }

      return {
        ...currentData,
        events: currentData.events.map((currentEvent) =>
          currentEvent.eventId === event.eventId
            ? {
                ...currentEvent,
                processStatus,
                lastHandledAt: updatedFault.lastHandledAt,
                lastHandledBy: updatedFault.lastHandledBy,
                lastHandleNote: updatedFault.lastHandleNote
              }
            : currentEvent
        ),
        faults: currentData.faults.map((currentFault) =>
          currentFault.faultId === updatedFault.faultId ? updatedFault : currentFault
        ),
        alarms: updatedAlarm
          ? currentData.alarms.map((currentAlarm) =>
              currentAlarm.alarmId === updatedAlarm.alarmId ? updatedAlarm : currentAlarm
            )
          : currentData.alarms
      };
    });
  }

  async function handleLoadAdvice(faultId: string) {
    if (appData?.adviceByFaultId[faultId] !== undefined || adviceLoadingFaultId === faultId) {
      return;
    }

    setAdviceLoadingFaultId(faultId);
    setAdviceErrorByFaultId((currentErrors) => ({ ...currentErrors, [faultId]: null }));

    try {
      const adviceResult = await getFaultAdvice(faultId);
      setAppData((currentData) => {
        if (!currentData) {
          return currentData;
        }

        return {
          ...currentData,
          adviceByFaultId: {
            ...currentData.adviceByFaultId,
            [faultId]: adviceResult.data
          }
        };
      });
    } catch {
      setAdviceErrorByFaultId((currentErrors) => ({ ...currentErrors, [faultId]: "维修建议读取失败，请稍后重试。" }));
    } finally {
      setAdviceLoadingFaultId((currentFaultId) => (currentFaultId === faultId ? null : currentFaultId));
    }
  }

  async function handleGenerateAdvice(faultId: string) {
    setAdviceLoadingFaultId(faultId);
    setAdviceErrorByFaultId((currentErrors) => ({ ...currentErrors, [faultId]: null }));

    try {
      const advice = await generateAdvice(faultId);
      setAppData((currentData) => {
        if (!currentData) {
          return currentData;
        }

        return {
          ...currentData,
          adviceByFaultId: {
            ...currentData.adviceByFaultId,
            [faultId]: advice
          },
          events: currentData.events.map((event) =>
            event.faultId === faultId ? { ...event, adviceStatus: advice.adviceStatus } : event
          )
        };
      });
    } catch {
      setAdviceErrorByFaultId((currentErrors) => ({ ...currentErrors, [faultId]: "维修建议生成失败，请稍后重试。" }));
    } finally {
      setAdviceLoadingFaultId((currentFaultId) => (currentFaultId === faultId ? null : currentFaultId));
    }
  }

  function handleLogout() {
    clearDemoAdminSession();
    setAppData(null);
    setIsAuthenticated(false);
    navigateToView(defaultView, { replace: true });
  }

  function navigateToView(view: ViewKey, options?: { replace?: boolean }) {
    setActiveView(view);

    const targetHash = `#${view}`;
    const currentHash = window.location.hash || "";

    if (currentHash === targetHash) {
      return;
    }

    if (options?.replace) {
      window.history.replaceState(null, "", targetHash);
      return;
    }

    window.history.pushState(null, "", targetHash);
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onAuthenticated={() => {
          setAppData(null);
          setIsAuthenticated(true);
        }}
      />
    );
  }

  const activeDataSource = appData ? dataSources[activeView] : null;

  return (
    <main className={isSidebarCollapsed ? "app-shell app-shell--sidebar-collapsed" : "app-shell"}>
      <aside className="sidebar">
        <div className="sidebar-main">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <Icon name="shield" size={20} />
            </span>
            <span className="brand-text">
              <span>EdgeEye</span>
              <strong>智能巡检平台</strong>
            </span>
            <button
              aria-label={isSidebarCollapsed ? "展开侧栏" : "收起侧栏"}
              aria-pressed={isSidebarCollapsed}
              className="sidebar-toggle"
              onClick={() => setIsSidebarCollapsed((collapsed) => !collapsed)}
              title={isSidebarCollapsed ? "展开侧栏" : "收起侧栏"}
              type="button"
            >
              <Icon name="chevron-right" size={16} />
            </button>
          </div>
          <p className="nav-section-label">主导航</p>
        </div>
        <nav className="nav-list" aria-label="主导航">
          {navItems.map((item) => (
            <button
              className={item.key === activeView ? "nav-item nav-item--active" : "nav-item"}
              key={item.key}
              onClick={() => navigateToView(item.key)}
              title={isSidebarCollapsed ? item.label : undefined}
              type="button"
            >
              <Icon name={item.icon} size={18} />
              <span className="nav-item__label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="avatar" aria-hidden="true">A</span>
            <span className="user-meta">
              <strong>管理员</strong>
              <span>admin · 在线</span>
            </span>
          </div>
          <button className="logout-button" onClick={handleLogout} type="button">
            <Icon name="log-out" size={16} />
            <span>退出登录</span>
          </button>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <span className="eyebrow">EdgeEye · 电力设备智能巡检</span>
            <h1>
              <Icon name={navItems.find((item) => item.key === activeView)?.icon ?? "grid"} size={24} />
              {navItems.find((item) => item.key === activeView)?.label}
            </h1>
          </div>
          <div className="topbar-actions">
            <div className="api-mode">
              <Icon name={!activeDataSource ? "activity" : activeDataSource === "api" ? "activity" : "alert-triangle"} size={14} />
              {!activeDataSource ? "连接中" : activeDataSource === "api" ? "系统已连接" : "后台服务暂不可用"}
            </div>
            <button
              aria-label={theme === "dark" ? "切换到浅色模式" : "切换到深色模式"}
              className="icon-button"
              onClick={toggleTheme}
              title={theme === "dark" ? "浅色模式" : "深色模式"}
              type="button"
            >
              <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
            </button>
          </div>
        </header>
        {page}
      </section>
    </main>
  );
}

function getViewFromLocation(): ViewKey {
  if (typeof window === "undefined") {
    return defaultView;
  }

  const hashView = window.location.hash.replace(/^#\/?/, "");
  return isViewKey(hashView) ? hashView : defaultView;
}

function isViewKey(value: string): value is ViewKey {
  return viewKeys.has(value as ViewKey);
}

function LoadingPage() {
  return (
    <div className="page-stack">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2>
              <Icon name="activity" size={18} />
              正在连接数据
            </h2>
            <p>正在同步巡检数据。</p>
          </div>
        </div>
        <div className="loading-state" aria-live="polite" aria-label="正在加载系统数据">
          <span className="loading-bar" />
          <span className="loading-bar loading-bar--medium" />
          <span className="loading-bar loading-bar--short" />
        </div>
      </section>
    </div>
  );
}

function createEmptyAppData(): AppData {
  const now = new Date().toISOString();

  return {
    dashboard: {
      deviceCount: 0,
      inspectionCount: 0,
      faultCount: 0,
      alarmCount: 0,
      criticalAlarmCount: 0,
      activeInspectionCount: 0,
      unresolvedFaultCount: 0,
      unresolvedAlarmCount: 0,
      dataFreshness: "offline",
      pageState: "error",
      latestInspectionAt: null,
      latestHighRiskAlarm: null
    },
    system: {
      camera: {
        status: "offline",
        lastFrameAt: null,
        lastHeartbeatAt: null,
        message: "服务暂不可用",
        degradedReason: null
      },
      atlas: {
        status: "offline",
        cpuUsage: 0,
        memoryUsage: 0,
        npuUsage: null,
        lastHeartbeatAt: null,
        message: "服务暂不可用",
        degradedReason: null
      },
      model: {
        status: "offline",
        modelVersion: "N/A",
        fps: 0,
        latencyMs: 0,
        lastHeartbeatAt: null,
        message: "服务暂不可用",
        degradedReason: null
      },
      backend: {
        status: "offline",
        lastHeartbeatAt: null,
        message: "后台服务未连接",
        degradedReason: null
      },
      updatedAt: now,
      dataFreshness: "offline",
      activeInspectionCount: 0,
      unresolvedFaultCount: 0,
      unresolvedAlarmCount: 0
    },
    snapshot: createEmptySnapshot(),
      events: [],
      adviceByFaultId: {},
    reports: [],
    devices: [],
    faults: [],
    alarms: []
  };
}

function createEmptySnapshot(): RealtimeSnapshot {
  return {
    inspectionId: "暂无巡检",
    inspectionStatus: "pending",
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
    imageWidth: 1280,
    imageHeight: 720,
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
