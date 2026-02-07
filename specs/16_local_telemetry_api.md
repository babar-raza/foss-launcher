# Local Telemetry API (centralized, non-negotiable)

## Purpose
The Local Telemetry Platform is the system-of-record for **auditing** and **accountability**.
All orchestrator activity, worker activity, gate runs, and every LLM call MUST be recorded so that:
- runs are reviewable end-to-end
- failures are debuggable without re-running
- every launch diff can be tied to a concrete git commit

**Authoritative API Reference:** `docs/reference/local-telemetry.md` (HTTP reference).

## Binding requirements
1) **Always-on**: Telemetry emission is required for every run.
2) **Idempotent writes**: Use `event_id` as the idempotency key for all POSTs.
3) **Commit traceability**: Once a commit exists, the system MUST associate it to telemetry runs.
4) **Non-fatal transport**: Telemetry transport failures must not crash the run; the system MUST buffer and retry.
5) **Deterministic run naming**: `run_id` format MUST be stable and reproducible from inputs.

## Service configuration
- Base URL: `TELEMETRY_API_URL` (default from reference: `http://localhost:8765`)
- Auth: optional (Bearer token) per `docs/reference/local-telemetry.md`

Client token configuration:
- If `run_config.telemetry.auth_token_env` is set, read that env var and send `Authorization: Bearer <token>` on telemetry requests.

Run config mapping (schemas/run_config.schema.json):
- `run_config.telemetry.endpoint_url` == Base URL (no path)

## Data model (how we use the API)
The API is **run-centric** (`/api/v1/runs`).
This system records different kinds of activities by creating **TelemetryRun records**:

### 1) One parent run per launch
Create a parent run at the start of `launch_start_run`:
- `agent_name`: `launch.orchestrator`
- `job_type`: `launch`
- `status`: `running`
- `run_id`: stable string (see below)
- `event_id`: UUIDv4

### 2) Child runs for every node, gate, and LLM call
For each unit of work, create a child TelemetryRun with:
- `parent_run_id`: the parent `run_id`
- `agent_name`: worker name (e.g., `launch.workers.RepoScout`, `launch.workers.SectionWriter.products`)
- `job_type`: one of:
  - `orchestrator_node` (clone_inputs, ingest_repo, build_facts, build_plan, merge_and_link, open_pr, finalize)
  - `worker` (RepoScout/FactsBuilder/SnippetCurator/IAPlanner/SectionWriter/LinkerAndPatcher/Fixer/Validator)
  - `gate` (schema, frontmatter, markdownlint, hugo_config, hugo_build, internal_links, external_links, snippets, truthlock, template_token_lint)
  - `llm_call` (every single model invocation)
  - `commit_service` (commit + open_pr)

This gives a complete audit trail using only the official `/api/v1/runs` surface.

### 3) LLM Call Telemetry (binding)

Every LLM API call MUST create a child TelemetryRun with detailed tracking of tokens, costs, and performance.

**Required Structure**:
- `job_type`: "llm_call"
- `parent_run_id`: Worker run_id (e.g., "run-001-w2-facts-builder")
- `agent_name`: Qualified path identifying the LLM caller (e.g., "launch.clients.llm_provider", "launch.w2.enrich_claims", "launch.w5.section_writer")
- `status`: "running" → "success" | "failure"

#### Required Fields on Start (POST /api/v1/runs)

- `event_id`: UUID4 (idempotency key)
- `run_id`: Stable ID (format: `{parent_run_id}-llm-{call_id}`)
- `agent_name`: Qualified agent path
- `job_type`: "llm_call"
- `start_time`: ISO8601 with timezone
- `context_json`: (see below)

#### Required Fields on Completion (PATCH /api/v1/runs/{event_id})

- `status`: "success" | "failure"
- `end_time`: ISO8601 with timezone
- `duration_ms`: Integer (total call latency in milliseconds)
- `metrics_json`: (see below)
- `error_summary`: String (if status=failure, short error message)
- `error_details`: String (if status=failure, full traceback)

#### context_json Structure for LLM Calls (binding)

```json
{
  "trace_id": "hex-uuid",
  "span_id": "hex-uuid",
  "parent_span_id": "hex-uuid",
  "call_id": "section_writer_my-page-slug",
  "model": "claude-sonnet-4-5",
  "provider_base_url": "https://api.anthropic.com/v1",
  "temperature": 0.0,
  "max_tokens": 4096,
  "prompt_hash": "sha256-hex",
  "evidence_path": "evidence/llm_calls/{call_id}.json"
}
```

**Field Definitions**:
- `trace_id`, `span_id`, `parent_span_id`: Correlation IDs for distributed tracing
- `call_id`: Stable identifier for this specific LLM call (used in evidence file naming)
- `model`: Model identifier (e.g., "claude-sonnet-4-5", "gpt-4")
- `provider_base_url`: API endpoint base URL
- `temperature`: Sampling temperature (0.0 = deterministic)
- `max_tokens`: Maximum tokens to generate
- `prompt_hash`: SHA256 hash of messages payload (for caching/deduplication)
- `evidence_path`: Relative path to evidence file containing full request/response

#### metrics_json Structure for LLM Calls (binding)

```json
{
  "input_tokens": 1500,
  "output_tokens": 3000,
  "prompt_tokens": 1500,
  "completion_tokens": 3000,
  "total_tokens": 4500,
  "api_cost_usd": 0.05,
  "finish_reason": "stop"
}
```

**Field Definitions**:
- `input_tokens`: Tokens in input (prompt + context)
- `output_tokens`: Tokens in output (completion)
- `prompt_tokens`: Alias for input_tokens (OpenAI compatibility)
- `completion_tokens`: Alias for output_tokens (OpenAI compatibility)
- `total_tokens`: Sum of input + output
- `api_cost_usd`: Estimated API cost in USD (see cost calculation below)
- `finish_reason`: Completion reason ("stop", "length", "tool_calls", "error")

#### Cost Calculation (binding)

Model pricing (as of 2026-02-07):
- Claude Sonnet 4.5: $3.00 per MTok input, $15.00 per MTok output
- Claude Opus 4: $15.00 per MTok input, $75.00 per MTok output
- Claude Haiku 4.5: $0.80 per MTok input, $4.00 per MTok output

Formula:
```
api_cost_usd = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
```

Example (Claude Sonnet 4.5, 1500 input, 3000 output):
```
cost = (1500 * 3.00 + 3000 * 15.00) / 1_000_000
     = (4500 + 45000) / 1_000_000
     = 0.0495 USD
```

#### Event Log Correlation (binding)

For every TelemetryRun with `job_type=llm_call`, the following events MUST be emitted to `runs/<run_id>/events.ndjson`:

- `LLM_CALL_STARTED` (before API call)
- `LLM_CALL_FINISHED` (on success)
- `LLM_CALL_FAILED` (on failure)

Event payloads MUST include matching `trace_id` and `span_id` for correlation.

See `specs/11_state_and_events.md` for detailed event payload schemas.

#### Graceful Degradation (binding)

ALL telemetry operations for LLM calls MUST follow the graceful degradation pattern:

1. **Non-Fatal Failures**: Telemetry failures MUST be logged as warnings and MUST NOT crash LLM operations
2. **Exception Handling**: All telemetry code paths MUST be wrapped in try/except blocks
3. **No Raise Statements**: Telemetry code MUST NOT raise exceptions (log warnings instead)
4. **Outbox Buffering**: When telemetry API unavailable, buffer to outbox and continue operation
5. **Optional Client**: TelemetryClient is always `Optional[TelemetryClient]`; if None, skip telemetry

Example error handling pattern:
```python
try:
    telemetry_client.create_run(...)
except TelemetryError as e:
    logger.warning("telemetry_create_run_failed", call_id=call_id, error=str(e))
    # NEVER raise - continue execution
except Exception as e:
    logger.warning("telemetry_unexpected_error", call_id=call_id, error=str(e))
    # NEVER raise - continue execution
```

#### Acceptance Criteria for LLM Call Telemetry

- Every LLM call has a corresponding TelemetryRun with `job_type=llm_call`
- Token usage and costs accurately recorded in `metrics_json`
- Trace/span IDs correlate with parent worker run
- Evidence files referenced in `context_json` exist and contain full request/response
- LLM_CALL_* events present in `events.ndjson` with matching trace IDs
- Telemetry failures do NOT crash LLM operations
- Offline mode works via outbox buffering

### Required fields for POST /api/v1/runs
Always supply:
- `event_id` (UUIDv4; reuse for retries)
- `run_id` (stable string)
- `agent_name`
- `job_type`
- `start_time` (ISO8601 with timezone)

Optional but recommended:
- `status` (defaults to `running` if omitted by implementation)
- `product`, `product_family`, `platform`, `subdomain`, `website_section`, `item_name`
- `git_repo`, `git_branch` (for aspose.org site repo)
- `metrics_json`, `context_json` (see below)

### Deterministic `run_id` rules
`run_id` MUST be stable and unique, but reproducible from inputs.
Recommended:
- `run_id = <utc_start_iso>-launch-<product_slug>-<github_ref_short>-<site_ref_short>`
- child run_id = `<parent_run_id>-<work_kind>-<stable_work_id>`

Avoid randomness in `run_id` (randomness belongs in `event_id`).

## Telemetry Retrieval API

### GET /telemetry/{run_id}

**Purpose:** Retrieve telemetry data for a specific run

**Request:**
- Method: GET
- Path: `/telemetry/{run_id}`
- Headers: `Accept: application/json`
- Body: None

**Response (Success):**
- Status: 200 OK
- Body: Telemetry JSON object (see schema: specs/schemas/telemetry.schema.json)

**Response (Not Found):**
- Status: 404 Not Found
- Body: `{"error": "run_id not found", "run_id": "abc123"}`

**Response (Error):**
- Status: 500 Internal Server Error
- Body: `{"error": "description"}`

**Example:**
```bash
curl http://localhost:8080/telemetry/20250125-1530
```

**Caching:** Results are cached per run_id (immutable after run completion)

**MCP Tool:** See specs/24_mcp_tool_schemas.md (tool schema: get_run_telemetry)

## What to store in metrics_json and context_json
Because the API does not expose a separate event stream endpoint, structured telemetry is stored in:

### metrics_json (numbers, counters)
- token counts and pricing counters (if available)
- latency_ms per LLM call
- items_discovered/succeeded/failed/skipped
- gate counts / error counts

### context_json (traceability and structured detail)
- `trace_id`, `span_id`, `parent_span_id` for local correlation
- node name (`clone_inputs`, `validate`, …)
- prompt hashes (`prompt_hash`, `input_hash`, `tool_schema_hash`)
- model info (`model`, `provider_base_url`, decoding params)
- artifact pointers (e.g., `runs/<run_id>/artifacts/product_facts.json`)
- failure classification (`error_class`, `retryable`, retry attempt)

**Rule:** `trace_id` and `span_id` MUST be present in `context_json` for every child run of kind `llm_call`, `gate`, and `orchestrator_node`.

## Status lifecycle
Use canonical statuses from the reference:
- `running`, `success`, `failure`, `partial`, `timeout`, `cancelled`

Update runs with PATCH /api/v1/runs/{event_id}:
- `status`
- `end_time`
- `duration_ms`
- `items_*`
- `output_summary` / `error_summary`
- `metrics_json` / `context_json`

## Commit association (non-negotiable)
Once a git commit is created (via commit service), the system MUST associate it with telemetry:

1) **Associate commit with the parent launch run**
- POST `/api/v1/runs/{parent_event_id}/associate-commit`

2) **Propagate commit to all child runs created before the commit**
- For each child `event_id`, call the same associate-commit endpoint.

Commit metadata:
- `commit_hash` (7–40 chars)
- `commit_source` in `{manual, llm, ci}` (use `llm` for agent-generated changes)
- `commit_author` and `commit_timestamp` when available

**Acceptance:** A reviewer can take the PR commit SHA and locate the corresponding parent launch run and all child runs.

## Failure Handling and Resilience (binding)

Telemetry is REQUIRED for all runs, but transport failures MUST be handled gracefully.

### Outbox Pattern (binding)

When telemetry POST fails (network error, timeout, 5xx error):
1. Append the failed request payload to `RUN_DIR/telemetry_outbox.jsonl`
2. Log WARNING: "Telemetry POST failed: {error}; payload written to outbox"
3. Continue run execution (do NOT fail the run due to telemetry transport failure)
4. Retry outbox flush at next stable state transition

### Outbox Flush Algorithm

At each stable state transition (PLAN_READY, DRAFT_READY, READY_FOR_PR):
1. Check if `RUN_DIR/telemetry_outbox.jsonl` exists and is non-empty
2. Read all lines (each line is a failed POST payload)
3. For each payload:
   a. Retry POST to telemetry API
   b. If success: remove line from outbox
   c. If failure after 3 retries: keep in outbox and continue
4. If all lines successfully flushed: delete `telemetry_outbox.jsonl`
5. If any lines remain after flush attempt: log WARNING and continue

### Bounded Retry Policy

Retry telemetry POSTs with exponential backoff:
- Max attempts: 3 per payload
- Backoff: 1s, 2s, 4s (no jitter needed for non-critical path)
- Timeout: 10s per POST attempt
- Do NOT retry on 4xx errors (client error indicates bad payload)

### Outbox Size Limits

To prevent unbounded outbox growth:
- Max outbox size: 10 MB
- If outbox exceeds 10 MB: truncate oldest entries and log ERROR
- Record truncation in telemetry event `TELEMETRY_OUTBOX_TRUNCATED` (when API becomes available)

### Failure Telemetry

When telemetry API is consistently unreachable:
- After 10 consecutive failures across multiple runs, emit system-level WARNING
- Write diagnostic report to `reports/telemetry_unavailable.md` with:
  - Outbox size and oldest entry timestamp
  - Number of failed POST attempts
  - Last successful telemetry POST timestamp
  - Suggested fixes (check API endpoint, network, auth token)

If the outbox cannot be flushed by run end:
- Mark the parent run `partial`
- Include `api_posted=false` and an `error_summary` explaining the telemetry outage

## Acceptance criteria
- Parent launch run exists and reaches a terminal status.
- Every orchestrator node, worker, gate, and LLM call has a child run.
- Every child run includes `trace_id` and `span_id` in `context_json`.
- Commit SHA is associated to the parent run and propagated to child runs.
- Outbox buffering exists and is flushed when API connectivity returns.
