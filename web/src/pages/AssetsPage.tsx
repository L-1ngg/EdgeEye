import type { ReactNode } from "react";

import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { StatusPill } from "../components/StatusPill";
import type { Alarm, DataSource, Device, DeviceType, Fault } from "../types/contracts";

interface AssetsPageProps {
  alarms: Alarm[];
  dataSource: DataSource;
  devices: Device[];
  faults: Fault[];
}

export function AssetsPage({ alarms, dataSource, devices, faults }: AssetsPageProps) {
  return (
    <div className="page-stack">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2><Icon name="database" size={18} />系统资源</h2>
            <p>按设备、故障、告警查看当前系统已有资源。</p>
          </div>
          <div className="heading-actions">
            <DataSourceBadge source={dataSource} />
            <span>{devices.length + faults.length + alarms.length} 条记录</span>
          </div>
        </div>
        <div className="resource-summary">
          <ResourceCounter label="设备" value={devices.length} />
          <ResourceCounter label="故障" value={faults.length} />
          <ResourceCounter label="告警" value={alarms.length} />
        </div>
      </section>

      <section className="resource-columns">
        <ResourceGroup title="设备" icon="camera" emptyText="暂无设备记录。">
          {devices.map((device) => (
            <article className="resource-card" key={device.deviceId}>
              <div className="resource-card__head">
                <strong>{formatDeviceName(device)}</strong>
                <StatusPill status={device.status} />
              </div>
              <span>{formatDeviceLocation(device.location)}</span>
              <small>{getDeviceTypeLabel(device.deviceType)} / {device.deviceId}</small>
            </article>
          ))}
        </ResourceGroup>

        <ResourceGroup title="故障" icon="alert-triangle" emptyText="暂无故障记录。">
          {faults.map((fault) => (
            <article className="resource-card" key={fault.faultId}>
              <div className="resource-card__head">
                <strong>{fault.faultType}</strong>
                <StatusPill status={fault.riskLevel} />
              </div>
              <span>{fault.deviceId} / {fault.bestFrameId}</span>
              <div className="resource-card__meta">
                <StatusPill status={fault.processStatus} />
                <small>{fault.priority} / {Math.round(fault.maxConfidence * 100)}%</small>
              </div>
            </article>
          ))}
        </ResourceGroup>

        <ResourceGroup title="告警" icon="shield" emptyText="暂无告警记录。">
          {alarms.map((alarm) => (
            <article className="resource-card" key={alarm.alarmId}>
              <div className="resource-card__head">
                <strong>{alarm.message}</strong>
                <StatusPill status={alarm.alarmLevel} />
              </div>
              <span>{alarm.deviceId} / {alarm.faultId}</span>
              <div className="resource-card__meta">
                <StatusPill status={alarm.processStatus} />
                <small>抑制 {alarm.suppressedCount} 次</small>
              </div>
            </article>
          ))}
        </ResourceGroup>
      </section>
    </div>
  );
}

const deviceTypeLabels: Record<DeviceType, string> = {
  meter: "仪表",
  insulator: "绝缘子",
  transformer: "变压器",
  switchgear: "开关柜",
  circuit_breaker: "断路器",
  unknown: "未知设备"
};

const deviceNameLabels: Record<string, string> = {
  "Line 2 insulator": "绝缘子",
  "Transformer bay": "变压器",
  "Switchgear cabinet": "开关柜"
};

const locationLabels: Record<string, string> = {
  "Line 2 Area A": "位置未配置",
  "Substation bay 1": "位置未配置",
  "Distribution room": "配电室"
};

function formatDeviceName(device: Device) {
  return deviceNameLabels[device.deviceName] ?? device.deviceName;
}

function formatDeviceLocation(location: string) {
  if (locationLabels[location]) {
    return locationLabels[location];
  }

  return /[A-Za-z]/.test(location) ? "位置未配置" : location;
}

function getDeviceTypeLabel(deviceType: DeviceType) {
  return deviceTypeLabels[deviceType] ?? deviceType;
}

function ResourceCounter({ label, value }: { label: string; value: number }) {
  return (
    <div className="resource-counter">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ResourceGroup({
  children,
  emptyText,
  icon,
  title
}: {
  children: ReactNode;
  emptyText: string;
  icon: "camera" | "alert-triangle" | "shield";
  title: string;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);

  return (
    <section className="panel resource-panel">
      <div className="panel-heading">
        <h2><Icon name={icon} size={18} />{title}</h2>
      </div>
      <div className="resource-list">
        {hasChildren ? children : <p className="empty-state">{emptyText}</p>}
      </div>
    </section>
  );
}
