import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import type { RealtimeSnapshot } from "../types/contracts";

interface RealtimePageProps {
  snapshot: RealtimeSnapshot;
}

export function RealtimePage({ snapshot }: RealtimePageProps) {
  const detection = snapshot.detections[0];
  const npuUsage = snapshot.performance.npuUsage;

  return (
    <div className="page-grid">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2>实时巡检</h2>
            <p>{snapshot.inspectionId}</p>
          </div>
          <StatusPill status={snapshot.resultStatus} />
        </div>
        <div className="inspection-canvas" role="img" aria-label="巡检检测画面占位图">
          <div className="grid-overlay" />
          {detection ? (
            <div className="detection-box">
              <span>{detection.category}</span>
              <strong>{Math.round(detection.confidence * 100)}%</strong>
            </div>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>帧信息</h2>
          <span>{snapshot.frameId}</span>
        </div>
        <div className="metric-grid metric-grid--compact">
          <MetricCard label="帧序号" value={snapshot.frameSeq} />
          <MetricCard label="关键帧" value={snapshot.isKeyFrame ? "是" : "否"} />
          <MetricCard label="上传原因" value={snapshot.uploadReason} />
          <MetricCard label="图像尺寸" value={`${snapshot.imageWidth} x ${snapshot.imageHeight}`} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>边缘性能</h2>
          <StatusPill status={snapshot.inspectionStatus} />
        </div>
        <div className="metric-grid metric-grid--compact">
          <MetricCard label="FPS" value={snapshot.performance.fps} />
          <MetricCard label="延迟" value={`${snapshot.performance.latencyMs}ms`} />
          <MetricCard label="CPU" value={`${snapshot.performance.cpuUsage}%`} />
          <MetricCard label="NPU" value={npuUsage === null ? "N/A" : `${npuUsage}%`} />
        </div>
      </section>
    </div>
  );
}
