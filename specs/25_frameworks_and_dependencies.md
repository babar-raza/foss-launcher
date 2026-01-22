# Frameworks and Dependencies (LangGraph + LangChain)

## Purpose
These specs define **what** the system must do. This document defines **how the implementation uses its core frameworks and deps**
so engineers and LLMs do not improvise architecture.

This is a binding implementation guide.

## Framework choices (binding)
### LangGraph: orchestration and state machine
Use **LangGraph** to implement the orchestrator as an explicit graph that matches:
- `specs/state-graph.md` (node list + routing)
- `specs/11_state_and_events.md` (state transitions + events)

LangGraph responsibilities:
- coordinate worker execution and fan-out drafting
- enforce single-writer rules for the site worktree (only `merge_and_link` mutates the worktree)
- implement the validate/fix loop with capped attempts
- provide resumability by loading the latest snapshot and replaying local events

### LangChain: LLM interface and worker pipelines
Use **LangChain** for model access and structured generation inside workers.
LangChain responsibilities:
- OpenAI-compatible chat model wrapper configuration (base URL + model + decoding)
- prompt templating and prompt hashing
- tool/function calling (only where explicitly allowed)
- structured output parsing to typed models
- callback hooks to emit telemetry for every LLM call

**Rule:** LangChain must not be used as the orchestrator. LangGraph owns orchestration.

## Dependency usage map (binding)
The implementation MUST pin versions (see “Version locking” below) and use deps for the following roles:

### Runtime + server
- **Python 3.12+**: primary runtime.
- **FastAPI**: MCP server HTTP surface (tools in `specs/14_mcp_endpoints.md`).
- **uvicorn**: dev/prod server runner (single process in development; production per deployment guide).
- **Typer**: optional CLI wrapper that calls the same internal services as MCP.

### LLM + orchestration
- **langgraph**: orchestrator state graph.
- **langchain-core**: prompts, output parsers, runnable composition.
- **langchain-openai** (or equivalent OpenAI-compatible LangChain provider package): chat model wrapper.

### Validation + schemas
- **pydantic**: typed internal models for request/response contracts and runtime validation.
- **jsonschema**: validate JSON artifacts strictly against `specs/schemas/*.schema.json`.

### HTTP + retries
- **httpx**: HTTP client for:
  - OpenAI-compatible LLM calls (if not handled by provider package)
  - Local Telemetry API (`specs/16_local_telemetry_api.md`)
  - GitHub commit service (`specs/17_github_commit_service.md`)
- **tenacity**: deterministic retry policy (bounded retries, exponential backoff, jitter disabled).

### Storage
- **sqlite3** (stdlib) or **SQLModel/SQLAlchemy** (optional): local event log (`runs/<run_id>/events.sqlite`) when using sqlite (default NDJSON log is `runs/<run_id>/events.ndjson`).
- **orjson** (optional): fast JSON encode/decode (must preserve ordering rules).

### Logging
- **structlog** (recommended) or stdlib logging: structured logs.
- **rich** (optional): human-readable console output only (must not affect artifacts).

## Version locking (binding)
Determinism depends on pinning.

Required:
- `config/toolchain.lock.yaml` pins system tools used by gates (Hugo, markdownlint, lychee).
- A Python lock file pins all Python deps.

Implementation MUST choose ONE Python lock approach:
- `uv` (`pyproject.toml` + `uv.lock`), or
- Poetry (`pyproject.toml` + `poetry.lock`)

**Rule:** The repo MUST fail CI if the Python lock file is missing or out of date.

## LangGraph implementation requirements
### Graph shape
The LangGraph graph MUST implement the nodes and ordering from `specs/state-graph.md`.
Minimum nodes:
1) clone_inputs
2) ingest_repo
3) build_facts
4) build_plan
5) draft_sections (fan-out)
6) merge_and_link
7) validate
8) fix
9) open_pr
10) finalize

### State
LangGraph state MUST include (at minimum):
- `run_id`, `event_id` (parent)
- current `run_state`
- section states
- artifact index (name -> sha256/path)
- open issues
- counters (fix attempts)

### Telemetry wrapping (binding)
Each LangGraph node execution MUST:
1) create a child TelemetryRun (job_type=`orchestrator_node`)
2) emit local events (`WORK_ITEM_STARTED`, `WORK_ITEM_FINISHED`, `RUN_STATE_CHANGED`)
3) PATCH the child TelemetryRun to terminal status

Node identifiers used in telemetry MUST be stable:
- store `node_name` and `stable_work_id` in `context_json`

## LangChain implementation requirements
### Model configuration
The chat model MUST be configured exclusively from `run_config.llm`:
- `api_base_url`
- `api_key_env` (optional)
- `model`
- decoding params (`temperature` MUST default to 0.0)
- request timeout

### Structured output (binding)
Workers that produce JSON artifacts MUST:
- generate JSON only (no markdown, no prose)
- validate output with **jsonschema** against the correct schema
- on failure: open a blocker issue and do NOT write invalid artifacts

### Tool calling policy
Tool calling is allowed ONLY when:
- tool schemas are deterministic and versioned
- tools cannot mutate the site worktree
- tool outputs are included in the EvidenceMap or local event log

Recommended tool use cases:
- `read_file_lines(path, start, end)` (repo + site worktree)
- `search_text(query)` (bounded, deterministic ordering)
- `list_dir(path)`

### Telemetry callbacks (binding)
LLM calls MUST be logged via:
- local events: `LLM_CALL_STARTED/FINISHED/FAILED`
- a child TelemetryRun per LLM call (`job_type=llm_call`)

Implement a LangChain callback handler (example name `TelemetryCallbackHandler`) that:
- hashes prompts/inputs/tool schemas
- records token usage and latency
- writes these into child TelemetryRun `metrics_json`/`context_json`

## Acceptance
- A developer can implement the orchestrator without guessing where LangGraph stops and LangChain starts.
- A developer can derive the exact dependency list and version-locking strategy.
- Telemetry for LangGraph nodes and LangChain LLM calls is complete and consistent.
