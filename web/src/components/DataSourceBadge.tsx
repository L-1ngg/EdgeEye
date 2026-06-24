import { Icon } from "./Icon";
import type { DataSource } from "../types/contracts";

interface DataSourceBadgeProps {
  source: DataSource;
}

export function DataSourceBadge({ source }: DataSourceBadgeProps) {
  if (source === "api") {
    return null;
  }

  return (
    <span className={`source-badge source-badge--${source}`}>
      <Icon name="alert-triangle" size={14} />
      数据暂不可用
    </span>
  );
}
