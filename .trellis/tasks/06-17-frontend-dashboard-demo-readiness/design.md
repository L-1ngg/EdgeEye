# Frontend dashboard demo readiness design

## Boundaries

- Frontend work stays under `web/` unless an API-contract mismatch blocks the
  screen from rendering correctly.
- `web/src/api/client.ts` remains the only fetch boundary.
- `web/src/types/contracts.ts` remains the shared frontend contract surface.
- Page components in `web/src/pages/` receive already-shaped data and focus on
  layout/composition.
- Reusable display primitives stay in `web/src/components/`.
- Styling remains plain CSS in `web/src/styles/global.css`.
- Minimal demo authentication stays entirely in the frontend. It must not add
  backend routes, password persistence, token refresh, or role management.

## Data Flow

```text
FastAPI endpoint or mock data
  -> web/src/api/client.ts
  -> App state
  -> page component props
  -> shared presentational components
```

Authentication flow:

```text
Login form
  -> compare against demo admin credential admin / edgeeye-admin
  -> store a demo session marker in browser storage
  -> render dashboard shell
  -> logout clears the marker
```

Existing backend coverage:

- `/api/dashboard`
- `/api/system/status`

Mock-only frontend data today:

- realtime snapshot
- fault/event list
- repair advice
- report summaries

The implementation should keep graceful fallback behavior so the frontend member
can demo the UI before every backend route is finished. Missing backend endpoints
should be represented at the API-client boundary with typed mock fallback, not
with backend code in this task.

## UI Approach

- Keep the current left navigation and operational workspace shell.
- Add a compact administrator login view before the shell. It should look like a
  utility screen for the inspection system, not a marketing hero.
- Prefer dense status cards, tables, event rows, and state panels over hero or
  marketing sections.
- Use explicit empty/stale/error/processing/no-frame states on the realtime
  page because those are part of the documented contract.
- Keep repeated data units card-like, but avoid wrapping whole pages in nested
  decorative cards.
- Keep text size stable and avoid viewport-scaled fonts.

## Template Research

Candidate dashboard templates checked during planning:

- TailAdmin React: React 19, TypeScript, Vite, Tailwind CSS dashboard template.
  Useful references: sidebar structure, metric cards, tables, stateful dashboard
  density. Not a direct fit because the current project does not use Tailwind
  and the template includes many unrelated dashboard/auth/calendar/chart pieces.
- shadcn-admin: Vite + shadcn/ui dashboard with responsive/accessibility focus
  and MIT license. Useful references: app shell, sidebar behavior, command-like
  utility patterns, dense internal-tool composition. Not a direct fit because it
  adds Tailwind, Radix/shadcn, TanStack Router/Query, Clerk-related auth, and a
  broader UI architecture than this task needs.
- slash-admin: React 19 + Vite + shadcn/ui + TypeScript with MIT license. Useful
  references: polished admin shell and component vocabulary. Not a direct fit
  because the dependency surface is very large for this small frontend.
- larry-xue/react-admin-dashboard: React 18 + Vite + Ant Design + Zustand + Ant
  Design Charts with MIT license. Useful references: Ant Design dashboard
  information architecture and chart/table composition. Not a direct fit because
  it would introduce Ant Design and a different React major.

Decision: use these as inspiration only. Rebuild the needed shell, cards,
status rows, tables, and state panels in the existing React/CSS codebase.

## Contract Notes

- JSON fields use `camelCase`.
- API enum values remain English lowercase or snake_case; page labels translate
  to Chinese through display helpers/components.
- Realtime display should consume `resultStatus` directly rather than guessing
  freshness from timestamps in page code.
- Fault center should consume `EventItem`/advice-shaped data rather than deriving
  alarms from raw detection boxes.

## Compatibility

- No backend migration is expected.
- No package-manager change is expected. Use Bun for frontend commands.
- If backend endpoints are added by another member later, page components should
  not need structural rewrites; the expected integration point is
  `web/src/api/client.ts`.
- Demo auth is intentionally not secure by itself. Real security requires
  backend authentication later.

## Risks

- If the UI only uses mock-only routes, it may look complete while backend
  integration remains partial.
- This is acceptable for this task because backend implementation is explicitly
  owned by another member.
- Copying a full dashboard template would likely add routing, state, styling,
  auth, and chart dependencies that are disproportionate to this project.
- Frontend-only auth can be bypassed by a determined user; label it and treat it
  as a demo gate only.
- Current frontend specs are partly scaffolded; implementation should follow
  actual code patterns and the populated guideline files that already exist.
