import { useMemo, useState } from "react";

import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { StatusPill } from "../components/StatusPill";
import type { DataSource, EventItem, ProcessStatus, RepairAdvice } from "../types/contracts";

interface FaultCenterPageProps {
  advice: RepairAdvice | null;
  dataSource: DataSource;
  events: EventItem[];
  onUpdateStatus: (event: EventItem, processStatus: ProcessStatus) => Promise<void>;
}

const processActions: Array<{ label: string; status: ProcessStatus }> = [
  { label: "处理中", status: "processing" },
  { label: "已解决", status: "resolved" },
  { label: "忽略", status: "ignored" }
];

export function FaultCenterPage({ advice, dataSource, events, onUpdateStatus }: FaultCenterPageProps) {
  const defaultEventId = useMemo(() => events[0]?.eventId ?? null, [events]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(defaultEventId);
  const [updatingStatus, setUpdatingStatus] = useState<ProcessStatus | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const selectedEvent = events.find((event) => event.eventId === selectedEventId) ?? events[0] ?? null;
  const unresolvedCount = events.filter((event) => event.processStatus !== "resolved").length;

  async function handleProcessAction(processStatus: ProcessStatus) {
    if (!selectedEvent) {
      return;
    }

    setUpdatingStatus(processStatus);
    setActionError(null);

    try {
      await onUpdateStatus(selectedEvent, processStatus);
    } catch {
      setActionError("状态更新失败，请确认后端接口可用。");
    } finally {
      setUpdatingStatus(null);
    }
  }

  return (
    <div className="page-grid">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2><Icon name="alert-triangle" size={18} />故障中心</h2>
            <p>{unresolvedCount} 个事件仍需处理。</p>
          </div>
          <div className="heading-actions">
            <DataSourceBadge source={dataSource} />
            <span>{events.length} 个事件</span>
          </div>
        </div>
        <div className="event-list">
          {events.map((event) => (
            <button
              className={event.eventId === selectedEvent?.eventId ? "event-row event-row--active" : "event-row"}
              key={event.eventId}
              onClick={() => setSelectedEventId(event.eventId)}
              type="button"
            >
              <div>
                <strong>{event.title}</strong>
                <span>{event.summary}</span>
                <small>
                  {event.deviceName} / {event.latestFrameId} / {formatTime(event.lastOccurredAt)}
                </small>
              </div>
              <div className="event-meta">
                <StatusPill status={event.riskLevel} />
                <StatusPill status={event.processStatus} />
                <span>{event.occurrenceCount} 次</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2><Icon name="shield" size={18} />维修建议</h2>
            <p>{selectedEvent?.deviceName ?? "暂无事件"}</p>
          </div>
          <StatusPill status={selectedEvent?.adviceStatus ?? "none"} />
        </div>
        {selectedEvent ? (
          <div className="detail-stack">
            <strong>{selectedEvent.title}</strong>
            <span>{selectedEvent.summary}</span>
            <div className="mini-grid">
              <span>故障：{selectedEvent.faultType}</span>
              <span>告警：{selectedEvent.alarmLevel ?? "未触发告警"}</span>
              <span>来源：{advice?.modelName ?? "暂无建议"}</span>
              <span>次数：{selectedEvent.occurrenceCount}</span>
            </div>
            <div className="process-actions" aria-label="故障处理操作">
              {processActions.map((action) => (
                <button
                  className={selectedEvent.processStatus === action.status ? "small-action small-action--active" : "small-action"}
                  disabled={updatingStatus !== null || selectedEvent.processStatus === action.status}
                  key={action.status}
                  onClick={() => void handleProcessAction(action.status)}
                  type="button"
                >
                  {updatingStatus === action.status ? "提交中" : action.label}
                </button>
              ))}
            </div>
            <small className="operator-note">
              操作员：admin{selectedEvent.lastHandledBy ? ` / 最近处理：${selectedEvent.lastHandledBy}` : ""}
            </small>
            {actionError ? <p className="form-error">{actionError}</p> : null}
            {advice ? (
              <>
                <strong>风险分析</strong>
                <span>{advice.riskAnalysis}</span>
                <strong>检查步骤</strong>
                <ul>
                  {advice.inspectionSteps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
                <strong>维修建议</strong>
                <ul>
                  {advice.maintenanceSuggestions.map((suggestion) => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
                <strong>安全注意事项</strong>
                <ul>
                  {advice.safetyNotes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="empty-state">暂无维修建议，请确认建议接口或后端生成任务是否可用。</p>
            )}
          </div>
        ) : (
          <p className="empty-state">暂无故障事件。</p>
        )}
      </section>
    </div>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
