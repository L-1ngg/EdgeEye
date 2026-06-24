import { useEffect, useState } from "react";

import { getCameraStreamUrl } from "../api/client";
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
const streamReconnectMs = 3000;

export function RealtimePage({ dataSource, snapshot }: RealtimePageProps) {
  const [frameLoadState, setFrameLoadState] = useState<FrameLoadState>("loading");
  const [streamRetryToken, setStreamRetryToken] = useState(0);
  const npuUsage = snapshot.performance.npuUsage;
  const hasResultFrame = snapshot.resultStatus === "ready" || snapshot.resultStatus === "stale";
  const baseStreamSource = getCameraStreamUrl();
  const streamSource = streamRetryToken === 0 ? baseStreamSource : `${baseStreamSource}?retry=${streamRetryToken}`;
  const hasStreamSource = baseStreamSource.length > 0;
  const canDisplayStream = frameLoadState === "loaded";
  const canDisplayRealtimeMetadata = hasResultFrame && canDisplayStream && snapshot.resultStatus === "ready";
  const canDisplayLastKnownMetadata = hasResultFrame && !canDisplayRealtimeMetadata;
  const canDisplayMetadata = canDisplayRealtimeMetadata || canDisplayLastKnownMetadata;
  const canOverlayDetections = canDisplayRealtimeMetadata;
  const shouldShowFrameFallback = !canDisplayStream;
  const averageConfidence = getAverageConfidence(snapshot.detections);
  const primaryDetection = snapshot.detections[0] ?? null;
  const metadataScope = canDisplayRealtimeMetadata ? "实时" : "最近一次";

  useEffect(() => {
    setFrameLoadState("loading");
  }, [streamSource]);

  useEffect(() => {
    setStreamRetryToken(0);
  }, [baseStreamSource]);

  useEffect(() => {
    if (frameLoadState !== "failed") {
      return;
    }

    const retryId = window.setTimeout(() => {
      setFrameLoadState("loading");
      setStreamRetryToken((currentToken) => currentToken + 1);
    }, streamReconnectMs);

    return () => {
      window.clearTimeout(retryId);
    };
  }, [frameLoadState]);

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
            style={{ aspectRatio: `${snapshot.imageWidth} / ${snapshot.imageHeight}` }}
          >
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
              src={streamSource}
            />
            <div className="grid-overlay" />
            {shouldShowFrameFallback ? (
              <FrameFallback
                frameLoadState={frameLoadState}
                hasFrameSource={hasStreamSource}
                status={snapshot.resultStatus}
              />
            ) : null}
            {canOverlayDetections
              ? snapshot.detections.map((detection) => (
                  <DetectionBox
                    detection={detection}
                    imageHeight={snapshot.imageHeight}
                    imageWidth={snapshot.imageWidth}
                    key={detection.detectionId}
                  />
                ))
              : null}
            <div className="video-live-tag">
              <span className={`live-dot live-dot--${canDisplayStream ? "good" : "warning"}`} aria-hidden="true" />
              {getStreamTagText(frameLoadState)}
            </div>
            {canDisplayLastKnownMetadata && canDisplayStream ? (
              <div className="canvas-alert">识别结果非实时，下方显示最近一次检测记录。</div>
            ) : null}
          </div>

          {canDisplayStream || hasResultFrame ? (
            <div className="video-caption">
              <span>{hasResultFrame ? `Frame ${snapshot.frameSeq ?? "-"}` : "Live stream"}</span>
              <span>{hasResultFrame ? formatTime(snapshot.receivedAt ?? snapshot.timestamp) : getRealtimeStateMessage(snapshot.resultStatus)}</span>
              <span>{snapshot.imageWidth} x {snapshot.imageHeight}</span>
            </div>
          ) : null}
        </div>
      </section>

      {canDisplayMetadata ? (
        <>
          {canDisplayLastKnownMetadata ? (
            <section className="last-known-result-banner" aria-live="polite">
              <span className="last-known-result-banner__icon" aria-hidden="true">
                <Icon name="alert-triangle" size={20} />
              </span>
              <div>
                <strong>当前不是实时识别数据</strong>
                <span>{getLastKnownResultMessage(frameLoadState, snapshot)}</span>
              </div>
            </section>
          ) : null}

          <section className="metric-grid realtime-summary-grid">
            <MetricCard label={`${metadataScope} YOLO 目标数`} value={snapshot.detections.length} tone={snapshot.detections.length > 0 ? "warning" : "good"} />
            <MetricCard label={`${metadataScope}平均置信度`} value={averageConfidence === null ? "N/A" : `${averageConfidence}%`} tone={averageConfidence !== null && averageConfidence >= 85 ? "warning" : "neutral"} />
            <MetricCard label={`${metadataScope}推理延迟`} value={`${snapshot.performance.latencyMs}ms`} detail="边缘端模型耗时" />
            <MetricCard label={`${metadataScope}视频帧率`} value={`${snapshot.performance.fps} FPS`} detail={snapshot.isKeyFrame ? "关键帧上传" : "普通帧采样"} />
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>
                  <Icon name="layers" size={18} />
                  {canDisplayRealtimeMetadata ? "YOLO 识别结果" : "最近一次 YOLO 识别结果"}
                </h2>
                <p>{getDetectionPanelDescription(canDisplayRealtimeMetadata, snapshot.detections.length)}</p>
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
              <div className="empty-state">{canDisplayRealtimeMetadata ? "当前画面未识别到目标或故障特征。" : "最近一次检测未识别到目标或故障特征。"}</div>
            )}
          </section>

          <section className="realtime-masonry">
            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Icon name="cpu" size={18} />
                  {canDisplayRealtimeMetadata ? "边缘推理性能" : "最近一次边缘推理性能"}
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
                  {canDisplayRealtimeMetadata ? "帧与采集信息" : "最近一次帧与采集信息"}
                </h2>
                <span>{snapshot.frameId ?? "尚无帧"}</span>
              </div>
              <div className="detail-stack">
                <InfoRow label="帧序号" value={snapshot.frameSeq ?? "-"} />
                <InfoRow label="接收时间" value={formatTime(snapshot.receivedAt ?? snapshot.timestamp)} />
                <InfoRow label="上传原因" value={snapshot.uploadReason} />
                <InfoRow label="关键帧" value={snapshot.isKeyFrame ? "是" : "否"} />
                <InfoRow label="有效时间窗口" value={snapshot.staleAfterMs ? `${snapshot.staleAfterMs}ms` : "N/A"} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <Icon name="activity" size={18} />
                  {canDisplayRealtimeMetadata ? "事件链路" : "最近一次事件链路"}
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
          frameLoadState={frameLoadState}
          hasFrameSource={hasStreamSource}
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

function getStreamTagText(state: FrameLoadState) {
  switch (state) {
    case "loaded":
      return "STREAM";
    case "loading":
      return "CONNECTING";
    case "failed":
      return "UNAVAILABLE";
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
      return "检测结果已过期。";
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
    return "暂未获得可展示的摄像头画面。";
  }

  if (status === "stale") {
    return "最近一次画面无法加载，请检查边缘端采集状态。";
  }

  return "摄像头画面加载失败，请检查边缘端采集状态。";
}

function getFrameDataUnavailableMessage(hasFrameSource: boolean, status: ResultStatus, frameLoadState: FrameLoadState) {
  if (status === "processing" || status === "no_frame" || status === "failed") {
    return getRealtimeStateMessage(status);
  }

  return getFrameFallbackMessage(hasFrameSource, status, frameLoadState);
}

function getLastKnownResultMessage(frameLoadState: FrameLoadState, snapshot: RealtimeSnapshot) {
  const receivedAt = formatTime(snapshot.receivedAt ?? snapshot.timestamp);

  if (frameLoadState !== "loaded") {
    return `摄像头实时画面不可用，下面保留最近一次检测记录，接收时间 ${receivedAt}。`;
  }

  if (snapshot.resultStatus === "stale") {
    return `检测结果已超过 ${snapshot.staleAfterMs ?? 3000}ms 有效时间窗口，下面保留最近一次检测记录，接收时间 ${receivedAt}。`;
  }

  return `下面保留最近一次检测记录，接收时间 ${receivedAt}。`;
}

function getDetectionPanelDescription(isRealtime: boolean, detectionCount: number) {
  if (isRealtime) {
    return detectionCount > 0 ? "按当前帧检测目标展示" : "当前帧没有检测目标";
  }

  return detectionCount > 0 ? "按最近一次检测记录展示" : "最近一次检测记录没有检测目标";
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
