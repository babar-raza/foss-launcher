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

## Buffering and retry behavior
Telemetry emission MUST be resilient:
- On network/transport failure, write the attempted payload to `runs/<run_id>/telemetry_outbox.jsonl`.
- Retry with exponential backoff.
- Flush the outbox at:
  - every state transition
  - before opening PR
  - on finalize

If the outbox cannot be flushed by run end:
- mark the parent run `partial`
- include `api_posted=false` and an `error_summary` explaining the telemetry outage

## Acceptance criteria
- Parent launch run exists and reaches a terminal status.
- Every orchestrator node, worker, gate, and LLM call has a child run.
- Every child run includes `trace_id` and `span_id` in `context_json`.
- Commit SHA is associated to the parent run and propagated to child runs.
- Outbox buffering exists and is flushed when API connectivity returns.
