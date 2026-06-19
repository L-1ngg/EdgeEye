# Frontend Hook Guidelines

> Hook usage patterns for the React dashboard.

---

## Overview

The frontend currently has one custom hook: `web/src/theme/useTheme.ts`.
General app data loading is intentionally not abstracted into a custom hook yet;
`web/src/App.tsx` owns the initial dashboard load and calls
`web/src/api/client.ts`, while pages receive typed data through props.

Do not add React Query, SWR, Zustand, Redux, or another state/data library
unless a future task explicitly justifies the repeated workflow it solves.

---

## Custom Hook Patterns

- Custom hook files live near their domain, for example
  `web/src/theme/useTheme.ts`.
- Hook names use the standard `use*` form.
- Hooks should return a small named object rather than positional tuples when
  there are multiple values/actions.
- Browser APIs must be guarded when they can run before the DOM exists.
- Persisted browser state should be handled inside the hook or its owning
  helper module, not scattered across pages.

Current example:

```typescript
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(resolveInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((previous) => (previous === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme };
}
```

`applyTheme()` is exported separately so `web/src/main.tsx` can apply the stored
theme before React renders and avoid a flash of the wrong color scheme.

---

## Data Fetching

- Keep `fetch` calls in `web/src/api/client.ts`.
- `App.tsx` owns the current initial load using `Promise.all` and then passes
  typed data into pages.
- Pages should render props and local UI state only; they should not retry,
  parse `ApiResponse<T>`, or call backend routes directly.
- `DataResult<T>` carries the API/unavailable source marker from the API
  boundary into the app shell.
- `getAdvice()` owns the GET-then-generate fallback for repair advice; pages do
  not implement that fallback.

---

## Local Interaction State

Use built-in React hooks for small page interactions:

- `useState` for selected event IDs, pending process actions, export status, and
  form errors.
- `useMemo` only for derived values that would otherwise be recomputed from
  props, such as the default selected event in `FaultCenterPage`.
- `useEffect` for DOM/event subscriptions and resource load-state resets, such
  as `hashchange` handling in `App.tsx` and frame source changes in
  `RealtimePage.tsx`.

---

## Common Mistakes

- Do not call `fetch` directly in page components.
- Do not create a custom hook just to wrap a single local `useState` unless the
  stateful workflow is reused.
- Do not read or write `localStorage` from multiple feature modules for the same
  concern; demo auth belongs in `web/src/auth/session.ts`, theme persistence in
  `web/src/theme/useTheme.ts`.
- Do not omit effect cleanup for window event listeners.
- Do not add a global state library for the current dashboard demo.
