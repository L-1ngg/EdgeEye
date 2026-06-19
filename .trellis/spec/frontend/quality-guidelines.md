# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend changes must keep the app buildable with Bun and preserve the
documented API contract boundary.

---

## Forbidden Patterns

- Do not call `fetch` directly from page components.
- Do not duplicate API response types inside individual pages.
- Do not commit `node_modules/`, `dist/`, or TypeScript build info files.
- Do not create marketing/landing-page screens for the monitoring product.

---

## Required Patterns

- Keep API calls in `web/src/api/`.
- Keep shared API types in `web/src/types/`.
- Keep reusable UI in `web/src/components/`.
- Keep page-level composition in `web/src/pages/`.
- Keep frontend-only demo authentication in `web/src/auth/`; do not imply it is
  backend-enforced security.
- Keep theme persistence and first-paint theme application in
  `web/src/theme/useTheme.ts` plus `web/src/main.tsx`.
- Use `DataSourceBadge` when a page can show API/unavailable source state.

---

## Testing Requirements

- Run the frontend build before committing:

```bash
cd web
bun run build
```

- When end-to-end tests are added, cover Dashboard, realtime stale/no-frame states, fault advice fallback, and report export states.
- There is no dedicated frontend test suite yet; do not claim frontend behavior
  is tested beyond `bun run build` unless a future task adds tests.

---

## Code Review Checklist

- Does the app still build with `bun run build`?
- Are API-facing types centralized and aligned with `docs/contracts.md`?
- Does UI remain usable at mobile widths?
- Are generated files excluded by `.gitignore`?
- Are direct browser APIs guarded or isolated in helpers/hooks?
- Did the change avoid committing `web/dist/`, `web/node_modules/`, or
  `*.tsbuildinfo`?

---

## Examples From This Codebase

Contract-safe API boundary:

```typescript
async function getPageItems<T>(path: string): Promise<T[]> {
  const page = await getJson<PageResult<T>>(path);
  return page.items;
}
```

Local page action state:

```tsx
const [exportingReportId, setExportingReportId] = useState<string | null>(null);
const [exportError, setExportError] = useState<string | null>(null);
```

Do not move that kind of state into a global store unless multiple independent
pages need to mutate it.
