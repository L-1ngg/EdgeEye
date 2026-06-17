# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Frontend code lives in `web/` and uses React + Vite + TypeScript. The first
screen is the operational dashboard shell, not a marketing page.

---

## Directory Layout

```text
web/
├── src/
│   ├── api/          # API client functions and fallback boundary
│   ├── auth/         # frontend-only demo authentication helpers
│   ├── components/   # shared presentational components
│   ├── data/         # typed demo/mock data
│   ├── pages/        # page-level views
│   ├── styles/       # global CSS
│   └── types/        # TypeScript contract types
├── package.json
├── bun.lock
└── vite.config.ts
```

---

## Module Organization

- Put reusable UI in `src/components/`.
- Put full-page views in `src/pages/`.
- Put API calls in `src/api/`; pages should not call `fetch` directly.
- Put frontend-only demo authentication helpers in `src/auth/`.
- Put shared contract types in `src/types/`.
- Put demo data in `src/data/` and keep it typed.

---

## Naming Conventions

- React component files use `PascalCase.tsx`.
- Non-component modules use `camelCase.ts` or descriptive lowercase names.
- API-facing TypeScript fields use `camelCase`.
- Component props should be declared with named `interface` types.

---

## Examples

- `web/src/App.tsx`
- `web/src/api/client.ts`
- `web/src/auth/session.ts`
- `web/src/types/contracts.ts`
- `web/src/pages/DashboardPage.tsx`
