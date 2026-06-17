# Implementation Plan

1. Load backend/frontend specs before editing code.
2. Confirm whether `backend/data/edgeeye.db` is tracked and remove it from git
   if tracked.
3. Add backend settings for uploads/reports static directories.
4. Mount `/uploads` and `/reports` static directories in `create_app()`.
5. Update backend Pydantic models to allow nullable NPU usage and validate bbox
   bounds at request validation time.
6. Add regression tests for nullable NPU usage and invalid bbox rejection.
7. Update backend docs and specs.
8. Run:
   - `uv run pytest` from `backend/`
   - `npm run build` from `web/` if frontend types change
   - `git diff --check`
9. Commit and push only this task's files.
