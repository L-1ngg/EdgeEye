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

---

## Testing Requirements

- Run the frontend build before committing:

```bash
cd web
bun run build
```

- When end-to-end tests are added, cover Dashboard, realtime stale/no-frame states, fault advice fallback, and report export states.

---

## Code Review Checklist

- Does the app still build with `bun run build`?
- Are API-facing types centralized and aligned with `docs/contracts.md`?
- Does UI remain usable at mobile widths?
- Are generated files excluded by `.gitignore`?
