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

## Scenario: Realtime Snapshot Polling

### 1. Scope / Trigger

- Trigger: the realtime inspection page needs live camera frame updates without
  changing backend API parameters or adding a stream endpoint.
- Applies to polling server-shaped realtime data in the current dashboard shell.

### 2. Signatures

- API boundary: `getRealtimeSnapshot(): Promise<DataResult<RealtimeSnapshot>>`
  in `web/src/api/client.ts`.
- State owner: `web/src/App.tsx` updates `appData.snapshot` and
  `dataSources.realtime`.
- Page boundary: `RealtimePage` receives an already-shaped
  `RealtimeSnapshot` and does not fetch.

### 3. Contracts

- Poll the existing latest-result chain through `getRealtimeSnapshot`; do not
  add query/body parameters for realtime refresh.
- Default poll interval is 1000 ms, matching the backend camera bridge default
  capture interval.
- A failed poll may mark only `dataSources.realtime` as `unavailable`; keep the
  last snapshot until a later successful poll replaces it.

### 4. Validation & Error Matrix

- User not authenticated -> no polling interval.
- Component unmount/logout -> clear interval and ignore in-flight responses.
- Backend unavailable -> set realtime data source to `unavailable`.
- Backend has no latest result -> API client returns a typed `no_frame`
  snapshot.

### 5. Good/Base/Bad Cases

- Good: app shell polls through the API client and pages stay presentational.
- Base: initial full load still populates all pages once.
- Bad: calling `fetch` directly from `RealtimePage` or duplicating
  latest-result fallback logic.

### 6. Tests Required

- Run TypeScript build after polling changes.
- Verify the backend latest-result smoke shows changing `frameId` values when
  hardware is available.

### 7. Wrong vs Correct

#### Wrong

```typescript
useEffect(() => {
  fetch("/api/inspections/latest-result");
}, []);
```

#### Correct

```typescript
const snapshotResult = await getRealtimeSnapshot();
setAppData((currentData) => currentData ? { ...currentData, snapshot: snapshotResult.data } : currentData);
```
