# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

This directory contains EdgeEye frontend conventions discovered from the React
dashboard under `web/`. Follow these files before changing the app shell, API
client, pages, components, theme hook, or contract types.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Active |
| [Component Guidelines](./component-guidelines.md) | Component patterns, props, composition | Active |
| [Hook Guidelines](./hook-guidelines.md) | Custom hooks, data fetching patterns | Active |
| [State Management](./state-management.md) | Local state, global state, server state | Active |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Active |
| [Type Safety](./type-safety.md) | Type patterns, validation | Active |

---

**Language**: All documentation should be written in **English**.

## Current Stack

- Language: TypeScript.
- UI framework: React.
- Build tool: Vite.
- Package manager: Bun.
- Styling: global CSS in `src/styles/global.css`, with reusable presentational
  components in `src/components/`.

## Pre-Development Checklist

- Read `directory-structure.md` before adding frontend modules.
- Read `component-guidelines.md`, `hook-guidelines.md`, and `type-safety.md` before adding views, hooks, or API types.
- Keep frontend API types aligned with `docs/contracts.md`.
- Run `cd web && bun run build` before committing frontend behavior changes.
