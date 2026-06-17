import { useEffect, useState } from "react";

import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { MetricCard } from "../components/MetricCard";
import { getStatusLabel, StatusPill } from "../components/StatusPill";
import type { DataSource, RealtimeSnapshot, ResultStatus } from "../types/contracts";

interface RealtimePageProps {
  dataSource: DataSource;
  snapshot: RealtimeSnapshot;
}

type Detection = RealtimeSnapshot["detections"][number];
type FrameLoadState = "loading" | "loaded" | "failed";

const resultTone: Record<ResultStatus, "good" | "warning" | "danger"> = {
  ready: "good",
  stale: "warning",
  no_frame: "warning",
  processing: "warning",
  failed: "danger"
};

export function RealtimePage({ dataSource, snapshot }: RealtimePageProps) {
  const [frameLoadState, setFrameLoadState] = useState<FrameLoadState>("loading");
  const npuUsage = snapshot.performance.npuUsage;
  const hasLiveFrame = snapshot.resultStatus === "ready" || snapshot.resultStatus === "stale";
  const frameSource = snapshot.annotatedImageUrl ?? snapshot.imageUrl;
  const canDisplayFrame = hasLiveFrame && Boolean(frameSource) && frameLoadState === "loaded";
  const shouldShowFrameFallback = hasLiveFrame && !canDisplayFrame;
  const averageConfidence = getAverageConfidence(snapshot.detections);
  const primaryDetection = snapshot.detections[0] ?? null;

  useEffect(() => {
    setFrameLoadState(frameSource ? "loading" : "failed");
  }, [frameSource]);

  return (
    <div className="realtime-flow">
      <section className="panel realtime-hero-panel">
        <div className="panel-heading realtime-hero-heading">
          <div>
            <h2>
              <Icon name="video" size={18} />
              边缘摄像头实时画面
            </h2>
            <p>{snapshot.inspectionId}</p>
          </div>
          <div className="heading-actions">
            <DataSourceBadge source={dataSource} />
            <StatusPill status={snapshot.resultStatus} />
          </div>
        </div>

        <div className="video-stage">
          <div
            className={`inspection-canvas inspection-canvas--${snapshot.resultStatus}`}
            role="img"
            aria-label="边缘摄像头实时巡检画面和 YOLO 检测框"
          >
            {frameSource && hasLiveFrame ? (
              <img
                alt=""
                className="video-frame"
                onError={(event) => {
                  setFrameLoadState("failed");
                  event.currentTarget.hidden = true;
                }}
                onLoad={(event) => {
                  setFrameLoadState("loaded");
                  event.currentTarget.hidden = false;
                }}
                src={frameSource}
              />
            ) : null}
            <div className="grid-overlay" />
            {hasLiveFrame && shouldShowFrameFallback ? (
              <FrameFallback
                frameLoadState={frameLoadState}
                hasFrameSource={Boolean(frameSource)}
                status={snapshot.resultStatus}
              />
            ) : null}
            {canDisplayFrame
              ? snapshot.detections.map((detection) => (
                  <DetectionBox
                    detection={detection}
                    imageHeight={snapshot.imageHeight}
                    imageWidth={snapshot.imageWidth}
                    key={detection.detectionId}
                  />
                ))
              : !hasLiveFrame ? (
              <div className="canvas-state">
                <strong>{getStatusLabel(snapshot.resultStatus)}</strong>
                <span>{getRealtimeStateMessage(snapshot.resultStatus)}</span>
              </div>
            ) : null}
            <div className="video-live-tag">
              <span className={`live-dot live-dot--${canDisplayFrame ? resultTone[snapshot.resultStatus] : "warning"}`} aria-hidden="true" />
              {canDisplayFrame ? getVideoTagText(snapshot.resultStatus) : "UNAVAILABLE"}
            </div>
            {snapshot.resultStatus === "stale" && canDisplayFrame ? (
              <div className="canvas-alert">实时结果已过期，当前显示最后一帧。</div>
            ) : null}
          </div>

          {canDisplayFrame ? (
            <div className="video-caption">
              <span>Frame {snapshot.frameSeq ?? "-"}</span>
              <span>{formatTime(snapshot.receivedAt ?? snapshot.timestamp)}</span>
              <span>{snapshot.imageWidth} x {snapshot.imageHeight}</span>
            </div>
          ) : null}
        </div>
      </section>

      {canDisplayFrame ? (
        <>
          <section className="metric-grid realtime-summary-grid">
            <MetricCard label="YOLO 目标数" value={snapshot.detections.length} tone={snapshot.detections.length > 0 ? "warning" : "good"} />
            <MetricCard label="平均置信度" value={averageConfidence === null ? "N/A" : `${averageConfidence}%`} tone={averageConfidence !== null && averageConfidence >= 85 ? "warning" : "neutral"} />
            <MetricCard label="推理延迟" value={`${snapshot.performance.latencyMs}ms`} detail="边缘端模型耗时" />
            <MetricCard label="视频帧率" value={`${snapshot.performance.fps} FPS`} detail={snapshot.isKeyFrame ? "关键帧上传" : "普通帧采样"} />
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  <Icon name="layers" size={18} />
                  YOLO 识别结果
                </h2>
                <p>{snapshot.detections.length > 0 ? "按当前帧检测目标展示" : "当前帧没有检测目标"}</p>
              </div>
              {primaryDetection ? <StatusPill status={primaryDetection.faultType ? "warning" : "ready"} /> : <StatusPill status="ready" />}
            </div>
            {snapshot.detections.length > 0 ? (
              <div className="detection-waterfall">
                {snapshot.detections.map((detection) => (
                  <article className="detection-card" key={detection.detectionId}>
                    <div className="detection-card__head">
                      <div>
                        <strong>{detection.category}</strong>
                        <span>{detection.deviceType ?? "unknown"}</span>
                      </div>
                      <span className="confidence-badge">{Math.round(detection.confidence * 100)}%</span>
                    </div>
                    <div className="detection-card__meta">
                      <span>故障特征</span>
                      <strong>{detection.faultType ?? "未发现"}</strong>
                    </div>
                    <div className="detection-card__meta">
                      <span>识别区域</span>
                      <strong>{formatBbox(detection.bbox)}</strong>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">当前画面未识别到目标或故障特征。</div>
            )}
          </section>

          <section className="realtime-masonry">
            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Icon name="cpu" size={18} />
                  边缘推理性能
                </h2>
                <StatusPill status={snapshot.inspectionStatus} />
              </div>
              <div className="metric-grid metric-grid--compact">
                <MetricCard label="CPU" value={`${snapshot.performance.cpuUsage}%`} />
                <MetricCard label="内存" value={`${snapshot.performance.memoryUsage}%`} />
                <MetricCard label="NPU" value={npuUsage === null ? "N/A" : `${npuUsage}%`} />
                <MetricCard label="模型 FPS" value={snapshot.performance.fps} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Icon name="camera" size={18} />
                  帧与采集信息
                </h2>
                <span>{snapshot.frameId ?? "尚无帧"}</span>
              </div>
              <div className="detail-stack">
                <InfoRow label="帧序号" value={snapshot.frameSeq ?? "-"} />
                <InfoRow label="接收时间" value={formatTime(snapshot.receivedAt ?? snapshot.timestamp)} />
                <InfoRow label="上传原因" value={snapshot.uploadReason} />
                <InfoRow label="关键帧" value={snapshot.isKeyFrame ? "是" : "否"} />
                <InfoRow label="新鲜度窗口" value={snapshot.staleAfterMs ? `${snapshot.staleAfterMs}ms` : "N/A"} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Icon name="activity" size={18} />
                  事件链路
                </h2>
                <StatusPill status={snapshot.eventStatus ?? "none"} />
              </div>
              <div className="detail-stack">
                <InfoRow label="事件键" value={snapshot.eventKey ?? "暂无"} />
                <InfoRow label="事件状态" value={snapshot.eventStatus ? getStatusLabel(snapshot.eventStatus) : "暂无"} />
                <InfoRow label="巡检状态" value={getStatusLabel(snapshot.inspectionStatus)} />
                <InfoRow label="样本窗口" value={formatSampleWindow(snapshot.sampleWindow)} />
              </div>
            </section>
          </section>
        </>
      ) : (
        <FrameDataUnavailablePanel
          frameLoadState={frameSource ? frameLoadState : "failed"}
          hasFrameSource={Boolean(frameSource)}
          status={snapshot.resultStatus}
        />
      )}
    </div>
  );
}

interface FrameFallbackProps {
  frameLoadState: FrameLoadState;
  hasFrameSource: boolean;
  status: ResultStatus;
}

function FrameFallback({ frameLoadState, hasFrameSource, status }: FrameFallbackProps) {
  const effectiveFrameLoadState = hasFrameSource ? frameLoadState : "failed";

  return (
    <div className="frame-fallback" aria-live="polite">
      <span className="frame-fallback__icon" aria-hidden="true">
        <Icon name="camera" size={26} />
      </span>
      <strong>{effectiveFrameLoadState === "loading" ? "正在连接画面" : "画面暂不可用"}</strong>
      <span>{getFrameFallbackMessage(hasFrameSource, status, effectiveFrameLoadState)}</span>
    </div>
  );
}

function FrameDataUnavailablePanel({ frameLoadState, hasFrameSource, status }: FrameFallbackProps) {
  return (
    <section className="panel frame-unavailable-panel" aria-live="polite">
      <div className="panel-heading">
        <div>
          <h2>
            <Icon name="layers" size={18} />
            当前帧数据暂不可展示
          </h2>
          <p>{getFrameDataUnavailableMessage(hasFrameSource, status, frameLoadState)}</p>
        </div>
        <StatusPill status={status} />
      </div>
      <div className="frame-unavailable-copy">
        <span className="frame-unavailable-copy__icon" aria-hidden="true">
          <Icon name="video" size={20} />
        </span>
        <div>
          <strong>检测框、YOLO 目标、置信度和边缘性能指标已暂停展示。</strong>
          <span>等当前摄像头帧成功加载后，页面会自动恢复实时识别数据。</span>
        </div>
      </div>
    </section>
  );
}

interface DetectionBoxProps {
  detection: Detection;
  imageWidth: number;
  imageHeight: number;
}

function DetectionBox({ detection, imageWidth, imageHeight }: DetectionBoxProps) {
  return (
    <div
      className={detection.faultType ? "detection-box detection-box--fault" : "detection-box"}
      style={toBoxStyle(detection.bbox, imageWidth, imageHeight)}
    >
      <span>{detection.category}</span>
      <strong>{Math.round(detection.confidence * 100)}%</strong>
    </div>
  );
}

interface InfoRowProps {
  label: string;
  value: string | number;
}

function InfoRow({ label, value }: InfoRowProps) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function toBoxStyle(bbox: [number, number, number, number], width: number, height: number) {
  const [x1, y1, x2, y2] = bbox;

  return {
    left: `${(x1 / width) * 100}%`,
    top: `${(y1 / height) * 100}%`,
    width: `${((x2 - x1) / width) * 100}%`,
    height: `${((y2 - y1) / height) * 100}%`
  };
}

function getAverageConfidence(detections: Detection[]) {
  if (detections.length === 0) {
    return null;
  }

  const total = detections.reduce((sum, detection) => sum + detection.confidence, 0);
  return Math.round((total / detections.length) * 100);
}

function getVideoTagText(status: ResultStatus) {
  switch (status) {
    case "ready":
      return "LIVE";
    case "stale":
      return "LAST FRAME";
    case "processing":
      return "INFERENCE";
    case "no_frame":
      return "WAITING";
    case "failed":
      return "FAILED";
    default:
      return "UNKNOWN";
  }
}

function getRealtimeStateMessage(status: ResultStatus) {
  switch (status) {
    case "processing":
      return "边缘端已收到画面，YOLO 模型正在生成检测结果。";
    case "no_frame":
      return "摄像头巡检已启动，但还没有可展示的视频帧。";
    case "failed":
      return "当前巡检结果生成失败，需要检查摄像头、边缘端或模型状态。";
    case "stale":
      return "数据已超过新鲜度窗口。";
    case "ready":
      return "实时结果可展示。";
    default:
      return "暂无状态说明。";
  }
}

function getFrameFallbackMessage(hasFrameSource: boolean, status: ResultStatus, frameLoadState: FrameLoadState) {
  if (frameLoadState === "loading") {
    return "正在连接边缘端摄像头画面，当前帧可见后再显示识别结果。";
  }

  if (!hasFrameSource) {
    return "后端尚未返回可展示的摄像头画面地址。";
  }

  if (status === "stale") {
    return "最后一帧地址无法加载，请检查静态文件或流服务。";
  }

  return "摄像头画面加载失败，请检查边缘端推流、上传路径或后端静态资源。";
}

function getFrameDataUnavailableMessage(hasFrameSource: boolean, status: ResultStatus, frameLoadState: FrameLoadState) {
  if (status === "processing" || status === "no_frame" || status === "failed") {
    return getRealtimeStateMessage(status);
  }

  return getFrameFallbackMessage(hasFrameSource, status, frameLoadState);
}

function formatBbox(bbox: [number, number, number, number]) {
  const [x1, y1, x2, y2] = bbox;
  return `${Math.round(x1)}, ${Math.round(y1)} -> ${Math.round(x2)}, ${Math.round(y2)}`;
}

function formatSampleWindow(sampleWindow: RealtimeSnapshot["sampleWindow"]) {
  if (!sampleWindow) {
    return "暂无";
  }

  return `${sampleWindow.frameCount} 帧 · ${formatTime(sampleWindow.startedAt)} - ${formatTime(sampleWindow.endedAt)}`;
}

function formatTime(value: string | null | undefined) {
  if (!value) {
    return "暂无";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}
