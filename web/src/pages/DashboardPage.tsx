import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import type { Dashboard, DataSource, SystemOverview } from "../types/contracts";

interface DashboardPageProps {
  dashboard: Dashboard;
  dataSource: DataSource;
  system: SystemOverview;
}

export function DashboardPage({ dashboard, dataSource, system }: DashboardPageProps) {
  const latestAlarm = dashboard.latestHighRiskAlarm;
  const atlasNpuUsage = system.atlas.npuUsage;

  return (
    <div className="page-grid">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2><Icon name="activity" size={18} />运行总览</h2>
            <p>最近巡检：{formatTime(dashboard.latestInspectionAt)}</p>
          </div>
          <div className="heading-actions">
            <DataSourceBadge source={dataSource} />
            <StatusPill status={dashboard.dataFreshness} />
          </div>
        </div>
        <div className="metric-grid">
          <MetricCard label="设备数" value={dashboard.deviceCount} />
          <MetricCard label="巡检数" value={dashboard.inspectionCount} />
          <MetricCard label="故障总数" value={dashboard.faultCount} tone="warning" />
          <MetricCard label="告警总数" value={dashboard.alarmCount} tone="danger" />
          <MetricCard label="活跃巡检" value={dashboard.activeInspectionCount} detail="正在接收边缘结果" />
          <MetricCard label="未处理故障" value={dashboard.unresolvedFaultCount} tone="warning" />
          <MetricCard label="未处理告警" value={dashboard.unresolvedAlarmCount} tone="danger" />
          <MetricCard label="严重告警" value={dashboard.criticalAlarmCount} tone="danger" />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2><Icon name="cpu" size={18} />系统状态</h2>
          <span>{formatTime(system.updatedAt)}</span>
        </div>
        <div className="status-list">
          <StatusRow label="摄像头" status={system.camera.status} detail={system.camera.message} meta={formatTime(system.camera.lastFrameAt)} />
          <StatusRow
            label="Atlas"
            status={system.atlas.status}
            detail={`${atlasNpuUsage === null ? "NPU N/A" : `NPU ${atlasNpuUsage}%`} / 内存 ${system.atlas.memoryUsage}%`}
          />
          <StatusRow label="模型" status={system.model.status} detail={`${system.model.modelVersion} · ${system.model.fps} FPS / ${system.model.latencyMs}ms`} />
          <StatusRow label="后端" status={system.backend.status} detail={system.backend.message} meta={formatTime(system.backend.lastHeartbeatAt)} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2><Icon name="alert-triangle" size={18} />最新高风险项</h2>
          {latestAlarm ? <StatusPill status={latestAlarm.processStatus} /> : null}
        </div>
        {latestAlarm ? (
          <div className="detail-stack">
            <strong>{latestAlarm.deviceName}</strong>
            <span>故障类型：{latestAlarm.faultType}</span>
            <span>风险等级：{latestAlarm.riskLevel}</span>
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

function StatusRow({ label, status, detail, meta }: { label: string; status: string; detail?: string | null; meta?: string }) {
  return (
    <div className="status-row">
      <div>
        <strong>{label}</strong>
        <span>{detail ?? "暂无说明"}</span>
        {meta ? <small>{meta}</small> : null}
      </div>
      <StatusPill status={status} />
    </div>
  );
}

function formatTime(value: string | null | undefined) {
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
