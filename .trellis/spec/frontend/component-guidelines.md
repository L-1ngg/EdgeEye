# Component Guidelines

> How components are built in this project.

---

## Overview

Components should support a monitoring/dashboard workflow. Favor dense,
scannable operational UI over landing-page or marketing composition.

---

## Component Structure

- Export named React components.
- Keep shared components focused on presentation.
- Keep page data assembly in page components or the app shell, not low-level components.

---

## Props Conventions

- Use named `interface` declarations for component props.
- Pass already-shaped contract data into page components.
- Avoid `any` and avoid broad type assertions for API payloads.

---

## Styling Patterns

- Initial skeleton uses global CSS in `web/src/styles/global.css`.
- Page sections should be unframed layout containers.
- Use bordered cards for repeated information units such as metrics, rows, and status items.

---

## Accessibility

- Navigation controls must be real `button` elements or links.
- Non-text visual placeholders should include an accessible label when meaningful.
- Text must fit at mobile widths; prefer responsive grid changes over viewport-scaled font sizes.

---

## Common Mistakes

- Do not create a landing page when the task is to build the working app.
- Do not put card-like page sections around other card-like UI elements.
