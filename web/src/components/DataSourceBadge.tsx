import { Icon } from "./Icon";
import type { DataSource } from "../types/contracts";

interface DataSourceBadgeProps {
  source: DataSource;
}

export function DataSourceBadge({ source }: DataSourceBadgeProps) {
  const isApi = source === "api";
  return (
    <span className={`source-badge source-badge--${source}`}>
      <Icon name={isApi ? "api" : "bug"} size={14} />
      {isApi ? "API 数据" : "接口不可用"}
    </span>
  );
}
