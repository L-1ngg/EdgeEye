# Member 4 Backend Database, Reports, and AI Advice

## Goal

Implement the member 4 backend deliverables defined by the project documents:
the FastAPI service must receive Atlas detection uploads, persist inspection
data, derive faults and alarms, expose frontend query APIs, generate repair
advice through a backend-only interface with rule-template fallback, and expose
inspection report list/detail/export APIs.

The work must follow `docs/contracts.md`, `docs/api-spec.md`,
`docs/openapi.yaml`, `docs/04-backend-api.md`, and the existing FastAPI/React
project structure.

## Confirmed Facts

- The repository already contains a FastAPI backend skeleton under `backend/`
  with uniform `ApiResponse` wrappers and demo dashboard/system routes.
- `docs/api-spec.md` and `docs/openapi.yaml` define the member 4 endpoint set:
  inspections, detection uploads, devices, faults, alarms, events, advice,
  reports, dashboard, and system status.
- `docs/contracts.md` requires camelCase JSON, ISO 8601 timestamps, unified
  success/error envelopes, idempotent `POST /api/detection/results`, backend
  derivation of `Fault` and `Alarm`, event aggregation by `eventKey`, and saved
  `Advice` records.
- The frontend currently calls backend `/dashboard` and `/system/status`, while
  realtime, events, and reports still use typed mock data.
- No external database or migration framework is configured yet. The safest
  backend database implementation for this repo state is SQLite via Python's
  standard library, with a configurable database path and deterministic test
  setup.

## Requirements

- Provide persistent storage for devices, inspections, detection results,
  faults, alarms, advice, and reports.
- Implement `POST /api/inspection/start`, `POST /api/inspections/{id}/finish`,
  `POST /api/inspections/{id}/fail`, and `GET /api/inspections`.
- Implement `POST /api/detection/results` with idempotency by
  `idempotencyKey`; duplicate identical uploads return the original result with
  `duplicate: true`, while conflicting duplicate keys return a clear conflict
  error.
- Store detection image URLs, detections, performance data, and latest-result
  metadata; expose `GET /api/inspections/{id}/latest-result`.
- Generate and aggregate backend `Fault` records from detection entries that
  include a `faultType`, updating the same event instead of creating repeated
  faults for the same `eventKey`.
- Generate and deduplicate `Alarm` records from faults according to documented
  risk/alarm defaults.
- Implement `GET /api/devices`, `GET /api/faults`, `GET /api/alarms`,
  `GET /api/events`, `PATCH /api/faults/{id}/status`, and
  `PATCH /api/alarms/{id}/status`.
- Implement `POST /api/advice/generate` and `GET /api/faults/{id}/advice`.
  API keys must not be exposed to the frontend; when no LLM provider is
  configured or a provider call fails, return a saved rule-template fallback
  advice record.
- Implement `GET /api/reports`, `GET /api/reports/{id}`, and
  `GET /api/reports/{id}/export`, generating a ready report when an inspection
  finishes.
- Keep existing `/api/health`, `/api/system/status`, and `/api/dashboard`
  behavior working, but source dashboard/system summary counts from stored data.
- Update frontend API client wiring so realtime, events, advice, and reports can
  consume the backend endpoints while retaining mock fallback behavior.
- Update docs/readme where needed so the runnable endpoints and environment
  variables are discoverable.

## Acceptance Criteria

- [ ] Backend tests cover the member 4 happy path: start inspection, upload
      detection result, create/update fault and alarm, generate advice, finish
      inspection, query report, and export report.
- [ ] Backend tests cover idempotency duplicate and conflict behavior for
      `POST /api/detection/results`.
- [ ] Backend tests cover list/detail endpoints used by the frontend:
      latest-result, devices, inspections, faults, alarms, events, dashboard,
      system status, reports, and advice lookup.
- [ ] API responses use the existing unified envelope and camelCase fields.
- [ ] `uv run pytest` passes from `backend/`.
- [ ] Frontend type-check/build passes after API client wiring changes.
- [ ] Changes are committed and pushed to `origin/main`.

## Notes

- This task intentionally scopes to member 4 deliverables. Atlas model
  deployment, detection model training, and frontend page redesign are owned by
  other members and should only be touched when needed for integration wiring.
