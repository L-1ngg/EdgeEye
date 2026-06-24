import { useEffect, useMemo, useState } from "react";

import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { StatusPill } from "../components/StatusPill";
import type { DataSource, EventItem, ProcessStatus, RepairAdvice } from "../types/contracts";

interface FaultCenterPageProps {
  adviceByFaultId: Record<string, RepairAdvice | null>;
  adviceErrorByFaultId: Record<string, string | null>;
  adviceLoadingFaultId: string | null;
  dataSource: DataSource;
  events: EventItem[];
  onGenerateAdvice: (faultId: string) => Promise<void>;
  onLoadAdvice: (faultId: string) => Promise<void>;
  onUpdateStatus: (event: EventItem, processStatus: ProcessStatus) => Promise<void>;
}

const processActions: Array<{ label: string; status: ProcessStatus }> = [
  { label: "处理中", status: "processing" },
  { label: "已解决", status: "resolved" },
  { label: "忽略", status: "ignored" }
];

type EvidenceLoadState = "idle" | "loaded" | "failed";

export function FaultCenterPage({
  adviceByFaultId,
  adviceErrorByFaultId,
  adviceLoadingFaultId,
  dataSource,
  events,
  onGenerateAdvice,
  onLoadAdvice,
  onUpdateStatus
}: FaultCenterPageProps) {
  const defaultEventId = useMemo(() => events[0]?.eventId ?? null, [events]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(defaultEventId);
  const [updatingStatus, setUpdatingStatus] = useState<ProcessStatus | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [generatingAdvice, setGeneratingAdvice] = useState(false);
  const [evidenceLoadState, setEvidenceLoadState] = useState<EvidenceLoadState>("idle");
  const selectedEvent = events.find((event) => event.eventId === selectedEventId) ?? events[0] ?? null;
  const selectedFaultId = selectedEvent?.faultId ?? null;
  const advice = selectedFaultId ? adviceByFaultId[selectedFaultId] ?? null : null;
  const adviceError = selectedFaultId ? adviceErrorByFaultId[selectedFaultId] : null;
  const isAdviceLoading = Boolean(selectedFaultId && adviceLoadingFaultId === selectedFaultId);
  const adviceStatus = advice?.adviceStatus ?? selectedEvent?.adviceStatus ?? "none";
  const unresolvedCount = events.filter((event) => event.processStatus !== "resolved").length;
  const evidenceImageUrl = selectedEvent?.latestImageUrl ?? "";
  const shouldShowEvidenceImage = evidenceImageUrl.length > 0 && evidenceLoadState !== "failed";

  useEffect(() => {
    if (!selectedFaultId) {
      return;
    }

    void onLoadAdvice(selectedFaultId);
  }, [onLoadAdvice, selectedFaultId]);

  useEffect(() => {
    setEvidenceLoadState(evidenceImageUrl ? "idle" : "failed");
  }, [evidenceImageUrl]);

  async function handleProcessAction(processStatus: ProcessStatus) {
    if (!selectedEvent) {
      return;
    }

    setUpdatingStatus(processStatus);
    setActionError(null);

    try {
      await onUpdateStatus(selectedEvent, processStatus);
    } catch {
      setActionError("状态更新失败，请稍后重试。");
    } finally {
      setUpdatingStatus(null);
    }
  }

  async function handleGenerateAdvice() {
    if (!selectedFaultId) {
      return;
    }

    setGeneratingAdvice(true);

    try {
      await onGenerateAdvice(selectedFaultId);
    } finally {
      setGeneratingAdvice(false);
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
          <StatusPill status={adviceStatus} />
        </div>
        {selectedEvent ? (
          <div className="detail-stack">
            <strong>{selectedEvent.title}</strong>
            <span>{selectedEvent.summary}</span>
            <div className="mini-grid">
              <span>故障：{selectedEvent.faultType}</span>
              <span>告警：{selectedEvent.alarmLevel ?? "未触发告警"}</span>
              <span>建议：{getAdviceSummary(adviceStatus, advice)}</span>
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
            {adviceError ? <p className="form-error">{adviceError}</p> : null}
            <div className="fault-evidence">
              <div className="fault-evidence__header">
                <strong>故障证据图</strong>
                <span>{selectedEvent.latestFrameId}</span>
              </div>
              {shouldShowEvidenceImage ? (
                <figure className="fault-evidence__figure">
                  <img
                    alt={`${selectedEvent.title} 的故障证据图`}
                    onError={() => setEvidenceLoadState("failed")}
                    onLoad={() => setEvidenceLoadState("loaded")}
                    src={evidenceImageUrl}
                  />
                  {evidenceLoadState !== "loaded" ? <span className="fault-evidence__loading">正在加载证据图</span> : null}
                </figure>
              ) : (
                <p className="empty-state">当前故障暂无可查看的证据图。</p>
              )}
            </div>
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
            ) : isAdviceLoading ? (
              <p className="empty-state">正在读取维修建议。</p>
            ) : (
              <div className="advice-empty-state">
                <p className="empty-state">当前故障还没有维修建议。</p>
                <button
                  className="small-action small-action--primary"
                  disabled={generatingAdvice}
                  onClick={() => void handleGenerateAdvice()}
                  type="button"
                >
                  {generatingAdvice ? "生成中" : "生成维修建议"}
                </button>
              </div>
            )}
          </div>
        ) : (
          <p className="empty-state">暂无故障事件。</p>
        )}
      </section>
    </div>
  );
}

function getAdviceSummary(status: string, advice: RepairAdvice | null) {
  if (advice) {
    return status === "fallback" ? "规则建议" : "已生成";
  }

  if (status === "generating") {
    return "生成中";
  }

  if (status === "failed") {
    return "生成失败";
  }

  return "待生成";
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
