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

export function StatusPill({ status }: StatusPillProps) {
  return <span className={`status-pill status-pill--${status}`}>{statusLabels[status] ?? status}</span>;
}
