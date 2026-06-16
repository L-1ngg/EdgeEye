import { StatusPill } from "../components/StatusPill";
import type { ReportSummary } from "../types/contracts";

interface ReportsPageProps {
  reports: ReportSummary[];
}

export function ReportsPage({ reports }: ReportsPageProps) {
  return (
    <section className="panel panel--wide">
      <div className="panel-heading">
        <div>
          <h2>报告中心</h2>
          <p>查看巡检报告生成状态和导出入口。</p>
        </div>
        <span>{reports.length} 份报告</span>
      </div>
      <div className="report-table">
        <div className="report-table__head">
          <span>报告</span>
          <span>巡检</span>
          <span>格式</span>
          <span>状态</span>
          <span>导出</span>
        </div>
        {reports.map((report) => (
          <div className="report-table__row" key={report.reportId}>
            <strong>{report.title}</strong>
            <span>{report.inspectionId}</span>
            <span>{report.format.toUpperCase()}</span>
            <StatusPill status={report.reportStatus} />
            <span>{report.url ? "可下载" : "等待生成"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
