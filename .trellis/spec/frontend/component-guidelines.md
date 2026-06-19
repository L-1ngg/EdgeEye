# Component Guidelines

> How components are built in this project.

---

## Overview

Components should support a monitoring/dashboard workflow. Favor dense,
scannable operational UI over landing-page or marketing composition.

---

## Component Structure

- Export named React components.
- Keep shared components focused on presentation.
- Keep page data assembly in page components or the app shell, not low-level components.
- Keep the minimal administrator login as a utility screen before the dashboard
  shell, not as a marketing page.
- Use `Icon` from `web/src/components/Icon.tsx` for the current no-dependency
  icon system; new icons are added to `IconName` and `ICON_PATHS`.
- Keep status display centralized through `StatusPill` and `getStatusLabel`
  instead of hard-coding label maps in each page.

---

## Props Conventions

- Use named `interface` declarations for component props.
- Pass already-shaped contract data into page components.
- Avoid `any` and avoid broad type assertions for API payloads.

---

## Styling Patterns

- Initial skeleton uses global CSS in `web/src/styles/global.css`.
- Page sections should be unframed layout containers.
- Use bordered cards for repeated information units such as metrics, rows, and status items.
- Keep domain-specific layout class names stable enough for existing CSS, for
  example `page-grid`, `panel`, `metric-grid`, `event-row`, and `video-stage`.

---

## Accessibility

- Navigation controls must be real `button` elements or links.
- Non-text visual placeholders should include an accessible label when meaningful.
- Text must fit at mobile widths; prefer responsive grid changes over viewport-scaled font sizes.

---

## Common Mistakes

- Do not create a landing page when the task is to build the working app.
- Do not put card-like page sections around other card-like UI elements.
- Do not present frontend-only demo authentication as production security.
- Do not duplicate Chinese status-label maps outside `StatusPill`.
- Do not pass raw `ApiResponse<T>` objects into components; components receive
  unwrapped contract data.

---

## Examples From This Codebase

Reusable metric card:

```tsx
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
```

Page component receiving already-shaped data:

```tsx
interface DashboardPageProps {
  dashboard: Dashboard;
  dataSource: DataSource;
  system: SystemOverview;
}
```
