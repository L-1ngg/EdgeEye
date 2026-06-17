import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import type { Dashboard, SystemOverview } from "../types/contracts";

interface DashboardPageProps {
  dashboard: Dashboard;
  system: SystemOverview;
}

export function DashboardPage({ dashboard, system }: DashboardPageProps) {
  const latestAlarm = dashboard.latestHighRiskAlarm;
  const atlasNpuUsage = system.atlas.npuUsage;

  return (
    <div className="page-grid">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2>运行总览</h2>
            <p>统计、系统状态和最近高风险项。</p>
          </div>
          <StatusPill status={dashboard.dataFreshness} />
        </div>
        <div className="metric-grid">
          <MetricCard label="设备数" value={dashboard.deviceCount} />
          <MetricCard label="巡检数" value={dashboard.inspectionCount} />
          <MetricCard label="故障数" value={dashboard.faultCount} tone="warning" />
          <MetricCard label="告警数" value={dashboard.alarmCount} tone="danger" />
          <MetricCard label="活跃巡检" value={dashboard.activeInspectionCount} />
          <MetricCard label="未处理故障" value={dashboard.unresolvedFaultCount} tone="warning" />
          <MetricCard label="未处理告警" value={dashboard.unresolvedAlarmCount} tone="danger" />
          <MetricCard label="严重告警" value={dashboard.criticalAlarmCount} tone="danger" />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>系统状态</h2>
          <span>{formatTime(system.updatedAt)}</span>
        </div>
        <div className="status-list">
          <StatusRow label="摄像头" status={system.camera.status} detail={system.camera.message} />
          <StatusRow label="Atlas" status={system.atlas.status} detail={atlasNpuUsage === null ? "NPU N/A" : `NPU ${atlasNpuUsage}%`} />
          <StatusRow label="模型" status={system.model.status} detail={`${system.model.fps} FPS / ${system.model.latencyMs}ms`} />
          <StatusRow label="后端" status={system.backend.status} detail={system.backend.message} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>最新高风险项</h2>
          {latestAlarm ? <StatusPill status={latestAlarm.processStatus} /> : null}
        </div>
        {latestAlarm ? (
          <div className="detail-stack">
            <strong>{latestAlarm.deviceName}</strong>
            <span>{latestAlarm.faultType}</span>
            <span>{latestAlarm.inspectionId}</span>
            <span>{formatTime(latestAlarm.createdAt)}</span>
          </div>
        ) : (
          <p className="empty-state">暂无高风险告警。</p>
        )}
      </section>
    </div>
  );
}

function StatusRow({ label, status, detail }: { label: string; status: string; detail?: string | null }) {
  return (
    <div className="status-row">
      <div>
        <strong>{label}</strong>
        <span>{detail ?? "暂无说明"}</span>
      </div>
      <StatusPill status={status} />
    </div>
  );
}

function formatTime(value: string | null) {
  if (!value) {
    return "暂无时间";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
