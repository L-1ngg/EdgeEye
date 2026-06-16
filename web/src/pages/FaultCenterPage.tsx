import { StatusPill } from "../components/StatusPill";
import type { EventItem, RepairAdvice } from "../types/contracts";

interface FaultCenterPageProps {
  events: EventItem[];
  advice: RepairAdvice;
}

export function FaultCenterPage({ events, advice }: FaultCenterPageProps) {
  return (
    <div className="page-grid">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2>故障中心</h2>
            <p>以后端聚合事件为主，不从原始检测结果推导告警。</p>
          </div>
          <span>{events.length} 个事件</span>
        </div>
        <div className="event-list">
          {events.map((event) => (
            <article className="event-row" key={event.eventId}>
              <div>
                <strong>{event.title}</strong>
                <span>{event.summary}</span>
                <small>{event.deviceName} / {event.latestFrameId}</small>
              </div>
              <div className="event-meta">
                <StatusPill status={event.riskLevel} />
                <StatusPill status={event.processStatus} />
                <span>{event.occurrenceCount} 次</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>维修建议</h2>
          <span>{advice.modelName}</span>
        </div>
        <div className="detail-stack">
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
        </div>
      </section>
    </div>
  );
}
