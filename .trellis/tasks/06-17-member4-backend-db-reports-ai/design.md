# Design: Member 4 Backend Database, Reports, and Advice

## Architecture

Keep the current FastAPI app and add member 4 routes under the existing
`/api` router. The backend remains a single-process demo service, but data
should be persisted in SQLite instead of hard-coded module fixtures.

Core modules:

- `app/models/inspection.py`: Pydantic request/response contracts for devices,
  inspections, detection uploads, latest result, faults, alarms, events, advice,
  and reports.
- `app/services/storage.py`: SQLite schema creation, seed data, row mapping, and
  repository operations.
- `app/services/inspection_service.py`: business flow for starting/finishing
  inspections, saving detection results, fault/alarm aggregation, advice
  generation, report generation, and dashboard/system summaries.
- `app/api/routes/*.py`: route files grouped by API area.

## Storage

Use Python `sqlite3` with one connection per operation and a configurable
database file path from `EDGEEYE_DATABASE_PATH`. The default path is
`backend/data/edgeeye.db`. Tests can point to a temporary file or reset the
default store.

Tables:

- `devices`: demo device catalog.
- `inspections`: lifecycle state and timestamps.
- `detection_results`: idempotency key, payload hash, frame metadata, image
  URLs, serialized detections/performance.
- `faults`: aggregated business fault event, including best evidence frame,
  occurrence counters, risk/alarm metadata, and process status.
- `alarms`: deduplicated alarm state per active fault/alarm key.
- `advice`: one saved advice record per fault for this version.
- `reports`: report list/detail/export metadata and generated summary.

Nested arrays/objects that are display payloads can be stored as JSON text to
avoid adding an ORM while still keeping the database durable.

## Detection Upload Flow

1. Validate request via Pydantic.
2. Canonicalize the payload to JSON and hash it.
3. If `idempotencyKey` exists:
   - same hash: return the existing result with `duplicate: true`;
   - different hash: raise `409 IDEMPOTENCY_CONFLICT`.
4. Ensure the inspection exists. If Atlas uploads before an explicit start,
   create a running inspection for that `inspectionId`.
5. Save the raw detection result.
6. For each detection with a `faultType`, apply local default rules:
   - `fire` => `critical`, `critical`, `P0`;
   - `smoke`, `person_intrusion`, `helmet_missing`, `surface_damage` => `high`,
     `warning`, `P1`;
   - `rust`, `foreign_object` => `medium`, `warning`, `P2`;
   - unknown/low confidence => `low`, `info`, `P3`.
7. Build `eventKey` from request `eventKey` or
   `{inspectionId}:{deviceId}:{faultType}`.
8. Update an existing active fault for that event or create a new fault.
9. Create or update a deduplicated alarm for non-`none` risk faults.
10. Return upload counters and latest inspection status.

## Advice Flow

The service exposes a backend-only LLM integration point without requiring a
real key for local tests. Configuration fields identify provider, API key,
timeout, and model name. The initial implementation uses a deterministic
rule-template generator by default and records `modelName: rule-template` with
`adviceStatus: fallback`. The interface keeps API keys in backend settings only,
so the frontend never receives secrets.

## Report Flow

When an inspection finishes, generate or refresh a ready HTML report record.
Reports include device, faults, alarms, advice records, exports metadata, and a
plain summary. PDF export is represented as a ready metadata response with a
stable download URL for the demo; no binary PDF generator is introduced.

## Compatibility

- Keep response envelopes compatible with existing `ApiResponse`.
- Preserve existing `/api/dashboard` and `/api/system/status` route paths.
- Retain mock fallback in frontend client so the UI remains usable when backend
  endpoints are unavailable.
- Do not introduce external database services or secrets.

## Rollback

The main rollback point is route registration. If the new service causes
startup failures, remove the member 4 route includes and the app returns to the
previous dashboard/system skeleton. SQLite data is stored under `backend/data/`
and is not required for source rollback.
