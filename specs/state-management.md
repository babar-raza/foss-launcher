# State management (event sourcing + snapshots)

## Purpose
This document defines how the system achieves:
- deterministic runs
- replay/resume
- auditability

**Authoritative contracts:** JSON schemas under `specs/schemas/`.
If this document ever conflicts with a schema file, the schema wins.

This document is binding.

## Storage model (two layers, required)
The implementation MUST persist state in two layers:

1) **Append-only local event log** (source of truth for replay/resume)
2) **Materialized snapshot** (fast current-state view)

### 1) Local event log (append-only)
Path:
- `runs/<run_id>/events.ndjson`

Format:
- one JSON object per line
- schema: `specs/schemas/event.schema.json`

Binding rules:
- events are append-only (no rewrites)
- events MUST be written before the snapshot update they imply
- event_id MUST be globally unique
- include `trace_id` and `span_id` for every event

### 2) Snapshot (materialized)
Path:
- `runs/<run_id>/snapshot.json`

Schema (binding):
- `specs/schemas/snapshot.schema.json`

Snapshot MUST contain:
- `run_id`
- `run_state`
- `section_states` (if applicable)
- `artifacts_index` (artifact_name → {path, sha256, schema_id, writer_worker, ts})
- `work_items` (see `specs/28_coordination_and_handoffs.md`)
- `issues` (open/resolved, stable ordering)

Binding rules:
- snapshot updates are atomic (write temp + rename)
- snapshot is derivable solely from events (no hidden state)

## Replay and resume

### Replay
Replay means rebuilding the snapshot from `events.ndjson` starting at `RUN_CREATED`.
A replay MUST be able to:
- restore the last known good run_state
- reconstruct artifacts_index (by reading `ARTIFACT_WRITTEN` events)
- reconstruct issues and their statuses
- reconstruct work item history

### Resume
Resume means continuing from the last stable snapshot:
- The orchestrator MUST validate `snapshot.json` against `snapshot.schema.json`.
- If invalid and `events.ndjson` exists, the orchestrator SHOULD rebuild the snapshot by replaying events.
- If rebuild fails (or event log is missing), the run MUST fail with a blocker issue `SnapshotInvalid`.
- The orchestrator reads `snapshot.json` and determines the next node from `state-graph.md`.
- Completed WorkItems MUST NOT be re-run unless:
  - the user forces it (explicit flag), or
  - an upstream artifact changed (sha256 mismatch) which invalidates downstream artifacts.

Invalidation rule (binding):
- if an upstream artifact changes, all dependent downstream artifacts MUST be marked stale and regenerated.

## Work items and determinism
Work items correspond to the orchestrator nodes and workers defined in:
- `specs/state-graph.md`
- `specs/21_worker_contracts.md`

Deterministic ordering rules MUST follow `specs/10_determinism_and_caching.md`.

## Relationship to Local Telemetry
- The local event log is required for replay/resume.
- The Local Telemetry API is required for audit/accountability and commit traceability.

See:
- `specs/16_local_telemetry_api.md`
- `docs/reference/local-telemetry.md`

## Acceptance
- replaying `events.ndjson` recreates `snapshot.json` exactly (byte-stable JSON formatting is recommended)
- resuming continues from the last stable node without repeating finished work
- failures still produce a complete event trail and final snapshot state
