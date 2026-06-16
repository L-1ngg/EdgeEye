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
- Keep enum-like strings as union types matching the docs, for example `RiskLevel` and `PageState`.
- Use typed mock data as the fallback shape for unavailable backend endpoints.

---

## Forbidden Patterns

- Do not use `any` for API payloads.
- Do not parse the same backend payload shape separately in multiple pages.
- Do not let pages derive alarm severity from raw detections; consume backend-shaped event/dashboard data.
