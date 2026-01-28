# State and Events

## Goal
Make runs replayable, resumable, and auditable.

- **Replay / resume** is powered by a local append-only event log (event sourcing).
- **Audit / accountability** is powered by the Local Telemetry API, recorded as TelemetryRun entries.

See:
- `specs/16_local_telemetry_api.md` (how to map activity to TelemetryRun records)
- `specs/schemas/event.schema.json` (local event log contract)

## State model
Run states:
- CREATED
- CLONED_INPUTS
- INGESTED
- FACTS_READY
- PLAN_READY
- DRAFTING
- DRAFT_READY
- LINKING
- VALIDATING
- FIXING
- READY_FOR_PR
- PR_OPENED
- DONE
- FAILED
- CANCELLED

Per-section states:
- NOT_STARTED
- OUTLINED
- DRAFTED
- MERGED_IN_WORKTREE
- DONE
- BLOCKED

## Central telemetry (non-negotiable)
All orchestrator nodes, workers, gates, and LLM calls MUST be recorded to the Local Telemetry API.

**Important:** The Local Telemetry API is run-centric. This system records activity by creating:
- one parent TelemetryRun per launch
- one child TelemetryRun per node, worker, gate, and LLM call

Raw local events do not need to be POSTed to the API as a separate stream.
Instead, events MUST be reflected in telemetry via:
- child run creation + status updates
- `context_json` containing `trace_id` and `span_id`

## Local event log (for replay/resume)
The system MUST also keep a local append-only event log for deterministic replay/resume.

Preferred (binding):
- `runs/<run_id>/events.ndjson` (one JSON object per line; schema: `specs/schemas/event.schema.json`)

Optional (allowed):
- `runs/<run_id>/events.sqlite` (when using sqlite as the storage backend)

If sqlite is used, the same event objects defined by `event.schema.json` MUST be persisted, and a deterministic export to NDJSON SHOULD be available for audits.

### Event log fields
Append-only events MUST validate against `specs/schemas/event.schema.json`:
- `event_id`
- `run_id`
- `ts` (ISO8601 with timezone)
- `type`
- `payload`
- `trace_id` (required)
- `span_id` (required)
- `parent_span_id` (optional)
- `prev_hash` and `event_hash` (optional but recommended)

## Required event types
Run lifecycle:
- RUN_CREATED
- INPUTS_CLONED
- ARTIFACT_WRITTEN
- WORK_ITEM_QUEUED
- WORK_ITEM_STARTED
- WORK_ITEM_FINISHED
- GATE_RUN_STARTED
- GATE_RUN_FINISHED
- ISSUE_OPENED
- ISSUE_RESOLVED
- RUN_STATE_CHANGED
- PR_OPENED
- RUN_COMPLETED
- RUN_FAILED

LLM operations (non-negotiable):
- LLM_CALL_STARTED (model, provider_base_url, prompt_hash, input_hash, tool_schema_hash)
- LLM_CALL_FINISHED (latency_ms, token_usage, finish_reason, output_hash)
- LLM_CALL_FAILED (error_class, retryable, latency_ms)

**Binding rule:** For every `LLM_CALL_*` local event, there MUST be a corresponding child TelemetryRun with:
- `job_type = llm_call`
- matching `trace_id`/`span_id` stored in `context_json`

## Snapshot
Write a materialized snapshot after each state transition.

Schema (binding): `specs/schemas/snapshot.schema.json`

Write a materialized snapshot after each state transition:
- run_state
- artifact index
- work items
- issues
- section states

## Acceptance
- replay from the local event log recreates the snapshot
- resume continues from last stable state without redoing completed work unless forced
- telemetry API contains a complete parent+child run trail and all LLM call runs

## Replay Algorithm (binding)

Replay recreates the final snapshot from the append-only event log without re-executing workers.

### Inputs
- `RUN_DIR/events.ndjson` (or `events.sqlite`)
- Initial snapshot: `{ run_id, run_state: CREATED, artifacts: [], work_items: [], issues: [], section_states: {} }`

### Algorithm Steps
1. **Load Events**: Read all events from `events.ndjson` in append order
2. **Validate Chain**: For each event, verify:
   - `event_hash = sha256(event_id + ts + type + payload + prev_hash)`
   - `prev_hash` matches previous event's `event_hash`
   - If validation fails, halt with error `EVENT_CHAIN_BROKEN`
3. **Apply Event Reducers**: For each event type, update snapshot:
   - `RUN_CREATED`: Initialize snapshot with run_id, timestamps
   - `RUN_STATE_CHANGED`: Update `snapshot.run_state = payload.new_state`
   - `ARTIFACT_WRITTEN`: Add to `snapshot.artifacts[]` with name, path, sha256, schema_id
   - `WORK_ITEM_QUEUED`: Add to `snapshot.work_items[]` with status=pending
   - `WORK_ITEM_STARTED`: Update work_item status=in_progress, started_at
   - `WORK_ITEM_FINISHED`: Update work_item status=completed, finished_at
   - `ISSUE_OPENED`: Add to `snapshot.issues[]` with status=OPEN
   - `ISSUE_RESOLVED`: Update issue status=RESOLVED, resolved_at
   - `GATE_RUN_FINISHED`: Update gate result in snapshot.gates[]
4. **Write Snapshot**: After processing all events, write `RUN_DIR/snapshot.json`
5. **Validate Snapshot**: Ensure snapshot validates against `snapshot.schema.json`

### Resume Algorithm (binding)

Resume continues from the last stable snapshot without re-executing completed work.

1. **Load Snapshot**: Read `RUN_DIR/snapshot.json`
2. **Identify Last Stable State**:
   - If `snapshot.run_state` is a stable state (PLAN_READY, DRAFT_READY, READY_FOR_PR), start from there
   - If `snapshot.run_state` is a transitional state (DRAFTING, LINKING, VALIDATING, FIXING), rewind to last stable state
3. **Filter Completed Work**:
   - Load `snapshot.work_items[]` with status=completed
   - Load `snapshot.artifacts[]` (all artifacts are considered completed)
   - Do NOT re-queue work items that are completed
4. **Resume Orchestrator**:
   - Set orchestrator state to `snapshot.run_state`
   - Queue only work_items with status=pending or in_progress
   - Continue from the current state transition

### Forced Full Replay (optional)

To force full replay from scratch (ignore snapshot):
1. Delete `RUN_DIR/snapshot.json`
2. Run replay algorithm from initial snapshot
3. Orchestrator will re-execute all work items (artifacts are cached, so LLM calls may be skipped if cache hits)
