# Fix inspection PDF wrapping and pagination

## Goal

Fix the inspection report PDF layout so long Chinese report content stays inside page bounds and remains readable when exporting from the report center.

## Requirements

- Scope is limited to backend PDF report generation for inspection reports.
- Keep the existing Chinese report content structure, title logic, and advice content aligned with the report center and fault center.
- Preserve the current built-in Chinese PDF font setup so exported PDFs still render Chinese text correctly.
- Long report lines must wrap within the printable width instead of overflowing past the page edge.
- PDF export must support pagination when wrapped report content exceeds one page.
- Add focused automated coverage for the PDF layout behavior to prevent regression.

## Acceptance Criteria

- [x] Exported inspection PDFs split long Chinese text into wrapped lines that fit within the page width.
- [x] Exported inspection PDFs create additional pages when report content exceeds the first page.
- [x] Existing report content assertions for title, sections, and maintenance advice still pass.
- [x] Backend pytest coverage passes for the report export flow.

## Out of Scope

- HTML report styling changes beyond keeping content aligned with the existing report document structure.
- Frontend report center UI changes.
- Reworking report wording, advice generation strategy, or report data model beyond what is required for PDF layout correctness.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
