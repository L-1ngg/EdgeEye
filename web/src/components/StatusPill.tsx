import type { SystemStatus } from "../types/contracts";

interface StatusPillProps {
  status: SystemStatus | string;
}

const statusLabels: Record<string, string> = {
  online: "在线",
  offline: "离线",
  degraded: "降级",
  error: "错误",
  unknown: "未知",
  fresh: "新鲜",
  stale: "过期",
  pending: "待处理",
  running: "运行中",
  completed: "已完成",
  cancelled: "已取消",
  processing: "处理中",
  resolved: "已处理",
  ignored: "已忽略",
  ready: "可用",
  generating: "生成中",
  failed: "失败",
  none: "无风险",
  low: "低风险",
  medium: "中风险",
  high: "高风险",
  critical: "严重",
  info: "提示",
  warning: "预警",
  fallback: "规则降级"
};

// States that convey "live / active" and earn a pulsing dot.
const LIVE_STATES = new Set(["online", "fresh", "ready"]);

export function getStatusLabel(status: string) {
  return statusLabels[status] ?? status;
}

export function StatusPill({ status }: StatusPillProps) {
  const isLive = LIVE_STATES.has(status);
  return (
    <span className={`status-pill status-pill--${status}`}>
      {isLive ? <span className="status-dot" aria-hidden="true" /> : null}
      {getStatusLabel(status)}
    </span>
  );
}
