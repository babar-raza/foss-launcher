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
- LLM_CALL_STARTED
- LLM_CALL_FINISHED
- LLM_CALL_FAILED

**Binding rule:** For every `LLM_CALL_*` local event, there MUST be a corresponding child TelemetryRun with:
- `job_type = llm_call`
- matching `trace_id`/`span_id` stored in `context_json`

### LLM_CALL_STARTED payload (binding)

Emitted immediately before making an LLM API call.

**Required fields**:
- `call_id`: String (stable identifier for this LLM call, used in evidence file naming)
- `model`: String (model name, e.g., "claude-sonnet-4-5", "gpt-4")
- `provider_base_url`: String (API base URL, e.g., "https://api.anthropic.com/v1")
- `prompt_hash`: String (SHA256 hash of messages payload for caching/deduplication)
- `temperature`: Number (sampling temperature, 0.0-1.0; 0.0 = deterministic)
- `max_tokens`: Integer (maximum tokens to generate, minimum 1)

**Optional fields**:
- `tool_schema_hash`: String (SHA256 hash of tools payload if function calling enabled)
- `response_format`: String (e.g., "json_object", "text")

**Example**:
```json
{
  "call_id": "section_writer_my-page-slug",
  "model": "claude-sonnet-4-5",
  "provider_base_url": "https://api.anthropic.com/v1",
  "prompt_hash": "a3f2...c901",
  "temperature": 0.0,
  "max_tokens": 4096,
  "response_format": "json_object"
}
```

### LLM_CALL_FINISHED payload (binding)

Emitted immediately after successful LLM API call completion.

**Required fields**:
- `call_id`: String (matches LLM_CALL_STARTED call_id)
- `latency_ms`: Integer (total call duration in milliseconds, minimum 0)
- `token_usage`: Object with required fields:
  - `input_tokens`: Integer (tokens in input/prompt)
  - `output_tokens`: Integer (tokens in output/completion)
  - `total_tokens`: Integer (sum of input + output)
- `finish_reason`: String (completion reason: "stop", "length", "tool_calls", "error")
- `output_hash`: String (SHA256 hash of response content)

**Optional fields**:
- `api_cost_usd`: Number (estimated API cost in USD based on model pricing)
- `tool_calls_count`: Integer (number of tool/function calls if tools were invoked)

**Example**:
```json
{
  "call_id": "section_writer_my-page-slug",
  "latency_ms": 5234,
  "token_usage": {
    "input_tokens": 1500,
    "output_tokens": 3000,
    "total_tokens": 4500
  },
  "finish_reason": "stop",
  "output_hash": "b9e1...d783",
  "api_cost_usd": 0.0495
}
```

### LLM_CALL_FAILED payload (binding)

Emitted when LLM API call fails with an error.

**Required fields**:
- `call_id`: String (matches LLM_CALL_STARTED call_id)
- `latency_ms`: Integer (duration until failure in milliseconds)
- `error_class`: String (exception class name, e.g., "LLMError", "HTTPError", "TimeoutError")
- `error_summary`: String (short error message for display)
- `retryable`: Boolean (whether error is retryable - true for network/timeout, false for auth/validation)

**Optional fields**:
- `error_details`: String (full traceback or stack trace for debugging)
- `http_status`: Integer (HTTP status code if API returned an error, e.g., 429, 500)

**Example**:
```json
{
  "call_id": "section_writer_my-page-slug",
  "latency_ms": 1205,
  "error_class": "HTTPError",
  "error_summary": "API rate limit exceeded",
  "retryable": true,
  "http_status": 429,
  "error_details": "Traceback (most recent call last):\n  ..."
}
```

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
