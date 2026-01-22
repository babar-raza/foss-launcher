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
