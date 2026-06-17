# State Management

> How state is managed in this project.

---

## Overview

The current frontend uses React component state only. There is no global state
library. Keep state local to `App.tsx` or the page component that owns the
interaction until a real repeated need appears.

---

## State Categories

- App shell state: active view, loaded page data, and data source markers live
  in `web/src/App.tsx`.
- Page interaction state: local UI controls such as selected fault event or
  realtime status preview live inside the page component.
- Demo authentication state: `web/src/auth/session.ts` owns the browser storage
  marker; `App.tsx` owns the current logged-in boolean.
- Server-shaped data: load through `web/src/api/client.ts` and keep typed
  fallback data in `web/src/data/`.

---

## When to Use Global State

Do not add a global state library for the current dashboard demo. Consider one
only if multiple independent pages need to update the same mutable state outside
the app shell.

---

## Server State

`web/src/api/client.ts` returns `DataResult<T>` for API-shaped data that may
fall back to mock data. Pages receive the already-shaped data plus a
`DataSource` marker and should not retry, parse, or fetch directly.

---

## Common Mistakes

- Do not call `fetch` from page components.
- Do not duplicate API fallback logic inside pages.
- Do not keep demo auth credentials in more than one module.
