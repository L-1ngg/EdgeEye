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

## Scenario: Realtime Stream + Snapshot Metadata

### 1. Scope / Trigger

- Trigger: the realtime inspection page needs smooth camera display while
  keeping detection/fault/performance metadata on existing backend contracts.
- Applies to MJPEG display URL wiring plus polling server-shaped realtime data
  in the current dashboard shell.

### 2. Signatures

- API boundary: `getRealtimeSnapshot(): Promise<DataResult<RealtimeSnapshot>>`
  in `web/src/api/client.ts`.
- Stream URL boundary: `getCameraStreamUrl(): string` in
  `web/src/api/client.ts`, returning `/api/camera/stream.mjpg`.
- State owner: `web/src/App.tsx` updates `appData.snapshot` and
  `dataSources.realtime`.
- Page boundary: `RealtimePage` receives an already-shaped
  `RealtimeSnapshot`, reads the stream URL from the API client, and does not
  call `fetch` directly.

### 3. Contracts

- Render the camera picture with `<img src={getCameraStreamUrl()} />`; the page
  should not read `snapshot.imageUrl` as the realtime video source.
- Poll the existing latest-result chain through `getRealtimeSnapshot` for
  detection boxes, faults, performance, and evidence URLs; do not add query/body
  parameters for realtime refresh.
- Default metadata poll interval is 1000 ms. It does not need to match the
  backend sample/evidence interval because the MJPEG stream carries the smooth
  live view.
- A failed poll may mark only `dataSources.realtime` as `unavailable`; keep the
  last snapshot until a later successful poll replaces it.
- Missing latest-result metadata should not hide a healthy MJPEG stream.

### 4. Validation & Error Matrix

- User not authenticated -> no polling interval.
- Component unmount/logout -> clear interval and ignore in-flight responses.
- Backend unavailable -> set realtime data source to `unavailable`.
- Backend has no latest result -> API client returns a typed `no_frame`
  snapshot.
- MJPEG stream unavailable -> `RealtimePage` shows camera fallback, but polling
  can keep reporting the latest backend metadata.

### 5. Good/Base/Bad Cases

- Good: app shell polls metadata through the API client, the page uses the API
  client stream URL for `<img>`, and realtime display remains independent from
  low-frequency latest-result samples.
- Base: initial full load still populates all pages once.
- Bad: calling `fetch` directly from `RealtimePage` or duplicating
  latest-result fallback logic.
- Bad: using `snapshot.imageUrl` as a 1 FPS video substitute when
  `/api/camera/stream.mjpg` is available.

### 6. Tests Required

- Run TypeScript build after polling changes.
- Verify the backend latest-result smoke shows changing `frameId` values when
  hardware is available.
- Verify the realtime page can display `/api/camera/stream.mjpg` even while
  `resultStatus` is `no_frame`.

### 7. Wrong vs Correct

#### Wrong

```typescript
useEffect(() => {
  fetch("/api/inspections/latest-result");
}, []);

const frameSource = snapshot.imageUrl;
```

#### Correct

```typescript
const snapshotResult = await getRealtimeSnapshot();
setAppData((currentData) => currentData ? { ...currentData, snapshot: snapshotResult.data } : currentData);

const streamSource = getCameraStreamUrl();
```
