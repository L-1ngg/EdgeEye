interface MetricCardProps {
  label: string;
  value: string | number;
  detail?: string;
  tone?: "neutral" | "good" | "warning" | "danger";
}

export function MetricCard({ label, value, detail, tone = "neutral" }: MetricCardProps) {
  return (
    <section className={`metric-card metric-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </section>
  );
}
