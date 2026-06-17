// Inline SVG icon system (Lucide-style, zero dependencies).
// All icons share a 24x24 viewBox and inherit text color via `currentColor`.

export type IconName =
  | "grid"
  | "video"
  | "alert-triangle"
  | "file-text"
  | "cpu"
  | "camera"
  | "layers"
  | "activity"
  | "database"
  | "api"
  | "bug"
  | "log-out"
  | "download"
  | "sun"
  | "moon"
  | "chevron-right"
  | "shield"
  | "gauge"
  | "circle";

// Each entry is the inner markup of a <svg> (paths/shapes only).
const ICON_PATHS: Record<IconName, string> = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  video: '<path d="m22 8-6 4 6 4V8Z"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
  "alert-triangle": '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2"/><path d="M15 2v2"/><path d="M9 20v2"/><path d="M15 20v2"/><path d="M2 9h2"/><path d="M2 15h2"/><path d="M20 9h2"/><path d="M20 15h2"/>',
  camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/><circle cx="12" cy="13" r="3"/>',
  layers: '<path d="m12.83 2.18-8 4a1 1 0 0 0 0 1.78l8 4a2 2 0 0 0 1.66 0l8-4a1 1 0 0 0 0-1.78l-8-4a2 2 0 0 0-1.66 0Z"/><path d="m2 12.5 9.17 4.32a2 2 0 0 0 1.66 0L22 12.5"/><path d="m2 17 9.17 4.32a2 2 0 0 0 1.66 0L22 17"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
  api: '<path d="M16 18 22 12 16 6"/><path d="M8 6 2 12l6 6"/><path d="m14 4-4 16"/>',
  bug: '<rect x="8" y="6" width="8" height="13" rx="4"/><path d="M9 6a3 3 0 0 1 6 0"/><path d="M8 11H3"/><path d="M21 11h-5"/><path d="M8 16H4"/><path d="M20 16h-4"/><path d="M11 19v2"/><path d="M13 19v2"/>',
  "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  "chevron-right": '<path d="m9 18 6-6-6-6"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  circle: '<circle cx="12" cy="12" r="10"/>'
};

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
  title?: string;
}

export function Icon({ name, size = 18, className, strokeWidth = 1.75, title }: IconProps) {
  const markup = { __html: ICON_PATHS[name] ?? ICON_PATHS.circle };
  return (
    <svg
      aria-hidden={title ? undefined : true}
      className={className}
      fill="none"
      focusable={false}
      height={size}
      role={title ? "img" : undefined}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      viewBox="0 0 24 24"
      width={size}
    >
      {title ? <title>{title}</title> : null}
      <g dangerouslySetInnerHTML={markup} />
    </svg>
  );
}
