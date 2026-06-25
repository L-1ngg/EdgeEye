import { useState } from "react";

import { DataSourceBadge } from "../components/DataSourceBadge";
import { Icon } from "../components/Icon";
import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import { exportReportPdf } from "../api/client";
import type { DataSource, ReportSummary } from "../types/contracts";

interface ReportsPageProps {
  dataSource: DataSource;
  reports: ReportSummary[];
}

export function ReportsPage({ dataSource, reports }: ReportsPageProps) {
  const [exportingReportId, setExportingReportId] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const readyCount = reports.filter((report) => report.reportStatus === "ready").length;
  const pendingCount = reports.filter((report) => report.reportStatus === "pending" || report.reportStatus === "generating").length;
  const failedCount = reports.filter((report) => report.reportStatus === "failed").length;

  async function handleExportPdf(report: ReportSummary) {
    setExportingReportId(report.reportId);
    setExportError(null);

    try {
      const exported = await exportReportPdf(report.reportId);

      if (!exported.downloadUrl) {
        setExportError("PDF 文件暂未生成，请稍后重试。");
        return;
      }

      const link = document.createElement("a");
      link.href = exported.downloadUrl;
      link.download = exported.fileName ?? `${report.reportId}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
    } catch {
      setExportError("PDF 导出失败，请稍后重试。");
    } finally {
      setExportingReportId(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel panel--wide">
        <div className="panel-heading">
          <div>
            <h2><Icon name="file-text" size={18} />报告中心</h2>
            <p>查看巡检报告生成状态和导出入口。</p>
          </div>
          <div className="heading-actions">
            <DataSourceBadge source={dataSource} />
            <span>{reports.length} 份报告</span>
          </div>
        </div>
        <div className="metric-grid metric-grid--three">
          <MetricCard label="可下载" value={readyCount} tone="good" />
          <MetricCard label="生成中/待生成" value={pendingCount} tone="warning" />
          <MetricCard label="生成失败" value={failedCount} tone={failedCount > 0 ? "danger" : "neutral"} />
        </div>
      </section>

      <section className="panel panel--wide">
        <div className="report-table">
          {exportError ? <p className="form-error">{exportError}</p> : null}
          <div className="report-table__head">
            <span>报告</span>
            <span>巡检</span>
            <span>类型</span>
            <span>状态</span>
            <span>导出</span>
          </div>
          {reports.length > 0 ? (
            reports.map((report) => (
              <div className="report-table__row" key={report.reportId}>
                <div>
                  <strong>{report.title}</strong>
                  <small>{formatTime(report.createdAt)}</small>
                </div>
                <span>{report.inspectionId}</span>
                <span>{getReportTypeLabel(report.format)}</span>
                <span className="report-table__status">
                  <StatusPill status={report.reportStatus} />
                </span>
                {report.reportStatus === "ready" ? (
                  <button className="table-action" onClick={() => void handleExportPdf(report)} type="button">
                    <Icon name="download" size={14} />
                    {exportingReportId === report.reportId ? "导出中" : "导出 PDF"}
                  </button>
                ) : (
                  <span className="table-action table-action--disabled">{getExportLabel(report.reportStatus)}</span>
                )}
              </div>
            ))
          ) : (
            <p className="empty-state">暂无报告记录。</p>
          )}
        </div>
      </section>
    </div>
  );
}

function getReportTypeLabel(format: ReportSummary["format"]) {
  switch (format) {
    case "html":
      return "在线报告";
    case "pdf":
      return "PDF 文件";
    default:
      return format;
  }
}

function getExportLabel(status: ReportSummary["reportStatus"]) {
  switch (status) {
    case "pending":
      return "待生成";
    case "generating":
      return "生成中";
    case "failed":
      return "需重试";
    case "ready":
      return "可下载";
    default:
      return "不可用";
  }
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
