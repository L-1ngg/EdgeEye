# Frontend dashboard demo readiness implementation plan

## Checklist

- [x] Resolve the open scope question with the user.
- [x] Refresh frontend context before coding with `trellis-before-dev`.
- [x] Use researched templates only as visual references; do not import a full
      template unless the user explicitly changes scope.
- [x] Add minimal frontend-only administrator login state and logout action.
- [x] Update frontend contract types for any API-shaped data the pages use.
- [x] Improve `web/src/api/client.ts` fallback behavior and add any approved
      frontend-only endpoint wrappers.
- [x] Improve page rendering for Dashboard, realtime inspection, fault center,
      and report center.
- [x] Update `web/src/styles/global.css` for responsive and state-specific UI.
- [x] Run frontend validation.
- [x] Revisit whether frontend specs need updates based on learned conventions.
- [x] Complete Trellis quality/finish steps before wrap-up.

## Validation Commands

```bash
cd web
bun run build
```

Backend validation is not required unless this task unexpectedly touches backend
files, which is currently out of scope.

## Risky Files

- `web/src/types/contracts.ts`: keep aligned with docs and backend payloads.
- `web/src/api/client.ts`: preserve the no-page-fetch boundary and typed fallback.
- `web/src/styles/global.css`: check mobile layout after large CSS changes.
- Auth/session helper code: keep it demo-only and do not imply production
  security.
- Backend files are out of scope for this task.

## Rollback Points

- Type/client changes can be rolled back independently from page styling.
- CSS-only layout changes should be kept separate enough to inspect quickly.
- Do not use backend edits as a rollback path; frontend should remain demoable
  with typed fallback data.
