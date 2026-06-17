# Backend Hardening and Documentation

## Goal

After pulling the latest teammate update, re-audit the member 4 backend against
the newly added Atlas planning task and improve backend robustness and
documentation for integration.

## Confirmed Facts

- `.codex/` project files are team-defined Codex/Trellis configuration and must
  be restored, retained, and referenced rather than left deleted.
- `git pull --ff-only origin main` brought in commit `1c74203`, adding member 1
  Atlas planning under `.trellis/tasks/06-17-edge-atlas/`.
- The new Atlas plan reiterates that edge uploads target
  `POST /api/detection/results`, that Atlas uploads `Detection` only, and that
  the backend derives `Fault`, `Alarm`, `Advice`, and reports.
- The Atlas plan explicitly allows NPU usage to be unavailable and represented
  as `null` or degraded diagnostic data.
- The project contract requires detection boxes to satisfy image bounds:
  `0 <= x1 < x2 <= imageWidth` and `0 <= y1 < y2 <= imageHeight`.
- `backend/data/edgeeye.db` currently appears in `rg --files`; local SQLite data
  should not be tracked source.

## Requirements

- Keep `.codex/` files restored in the working tree.
- Remove any tracked local SQLite runtime database file from source while
  retaining `.gitignore` protection for future generated DB files.
- Allow backend detection upload performance payloads to accept `npuUsage: null`
  for boards where NPU metrics cannot be read.
- Validate every uploaded detection bbox against the uploaded image dimensions
  and reject invalid payloads with the existing unified validation error shape.
- Expose or document backend static directories for `/uploads` and `/reports`
  so Atlas-generated `imageUrl`, `annotatedImageUrl`, and report URLs have a
  clear serving convention during integration.
- Improve backend-facing docs to cover persistence, image URL/static directory
  expectations, nullable NPU metrics, bbox validation, LLM advice provider
  configuration, and verification commands.

## Acceptance Criteria

- [ ] `backend/data/edgeeye.db` is no longer tracked.
- [ ] Backend accepts upload payloads where `performance.npuUsage` is `null`.
- [ ] Backend rejects invalid bbox coordinates with HTTP 400 and
      `VALIDATION_ERROR`.
- [ ] Static `/uploads` and `/reports` directories are configured and documented.
- [ ] Backend docs mention environment variables and integration expectations
      needed by Atlas/member 1.
- [ ] `cd backend && uv run pytest` passes.
- [ ] `cd web && npm run build` passes if frontend types are touched.
- [ ] Changes are committed and pushed to `origin/main`.

## Out of Scope

- Implementing the member 1 Atlas edge app.
- Adding multipart image upload to `POST /api/detection/results`.
- Replacing SQLite with an external database or migration framework.
