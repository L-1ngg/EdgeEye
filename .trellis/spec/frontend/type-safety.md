# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend uses TypeScript in strict mode. API-facing types should mirror
`docs/contracts.md` and remain centralized so pages do not redefine payload
shapes.

---

## Type Organization

- Shared API and contract types live in `web/src/types/contracts.ts`.
- Local component-only props can be defined in the component file.
- Mock data in `web/src/data/` must import and satisfy the shared types.

---

## Validation

- Runtime validation is not part of the initial skeleton.
- When added, validation should live at the API client boundary, not inside every page.

---

## Common Patterns

- Use `ApiResponse<T>` for successful backend responses.
- Use `PageResult<T>` for backend list endpoints, then unwrap `items` inside
  `src/api/client.ts`; pages should receive arrays or already-shaped objects.
- Use `DataResult<T>` when the frontend can fall back from an unavailable API
  endpoint to typed mock data.
- Keep enum-like strings as union types matching the docs, for example `RiskLevel` and `PageState`.
- Use typed mock data as the fallback shape for unavailable backend endpoints.

---

## Scenario: Backend API Client Boundary

### 1. Scope / Trigger

- Trigger: frontend now consumes member 4 backend list/detail endpoints for
  realtime snapshots, events, advice, and reports.

### 2. Signatures

- `getJson<T>(path: string): Promise<T>` unwraps `ApiResponse<T>`.
- `getPageItems<T>(path: string): Promise<T[]>` unwraps `PageResult<T>.items`.
- Pages import contract types from `src/types/contracts.ts`.

### 3. Contracts

- Backend report list fields are `reportStatus`, `createdAt`, and `url`.
- Backend advice includes `adviceStatus`.
- `EventItem.alarmId` can be `null`.
- `AtlasStatus.npuUsage` and `RealtimeSnapshot.performance.npuUsage` can be
  `null`; dashboard/realtime UI should render `N/A` rather than `null%`.
- Mock fallback objects must satisfy the same interfaces as API responses.

### 4. Validation & Error Matrix

- Backend request fails -> API client returns typed mock fallback.
- Advice GET returns not ready -> client may call `POST /advice/generate`, then
  falls back to mock if generation fails.
- Missing latest inspection/result -> realtime page uses `mockRealtimeSnapshot`.

### 5. Good/Base/Bad Cases

- Good: API client owns fallback and page components only render typed data.
- Base: list endpoints return `PageResult<T>` and client passes `items` to pages.
- Bad: page component calls `fetch` or reads `body.data.items` directly.

### 6. Tests Required

- Run `npm run build` after changing API-facing types.
- Keep mock data compiling against shared interfaces.
- Add or update display handling when a backend numeric metric becomes
  nullable.

### 7. Wrong vs Correct

#### Wrong

```typescript
const body = await response.json();
setReports(body.data.items as any[]);
```

#### Correct

```typescript
export async function getReports(): Promise<ReportSummary[]> {
  try {
    return await getPageItems<ReportSummary>("/reports");
  } catch {
    return mockReports;
  }
}
```

---

## Forbidden Patterns

- Do not use `any` for API payloads.
- Do not parse the same backend payload shape separately in multiple pages.
- Do not let pages derive alarm severity from raw detections; consume backend-shaped event/dashboard data.
