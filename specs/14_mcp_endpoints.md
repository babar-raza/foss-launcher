# MCP Endpoints (non-negotiable)

## Requirement
All system features MUST be available via MCP tools.
CLI may exist, but MCP is required for full feature parity.

## Minimum MCP tool surface
- launch_start_run(run_config) -> { run_id }
- launch_start_run_from_product_url(url) -> { run_id, derived_config } — quickstart: derives run_config from Aspose product page URL
- launch_start_run_from_github_repo_url(github_repo_url) -> { run_id, derived_config } — quickstart: derives run_config from public GitHub repo URL
- launch_get_status(run_id) -> { state, section_states, open_issues, artifacts }
- launch_get_artifact(run_id, artifact_name) -> { content, content_type, sha256 }
- launch_validate(run_id) -> { validation_report }
- launch_fix_next(run_id) -> { applied_patch_ids, remaining_issues }
- launch_resume(run_id) -> { state }
- launch_cancel(run_id) -> { cancelled: true }
- launch_open_pr(run_id) -> { pr_url, branch }
- launch_list_runs(filter?) -> { runs[] }

## Backward compatibility
- `launch_start_run_from_url` is a deprecated alias for `launch_start_run_from_product_url`. Implementations SHOULD support both names but new code MUST use the explicit name.

## Binding behavior
- MCP tools MUST emit telemetry events for every call.
- MCP tools MUST enforce allowed_paths and forbid out-of-scope edits.
- MCP tools MUST be deterministic: same inputs produce same outputs (within expected nondeterminism limits already defined in specs).

## MCP Server Contract (binding)

### Server Configuration
- Protocol: STDIO (standard input/output JSON-RPC)
- Server name: `foss-launcher-mcp`
- Server version: Match launcher version (e.g., `0.1.0`)
- Capabilities: `tools`, `resources` (no prompts or sampling required)

### Authentication (binding)
- MCP servers running over STDIO do not require auth (client controls process)
- If exposed via HTTP transport (optional), MUST require bearer token auth
- Token validation MUST use the same pattern as commit service (specs/17_github_commit_service.md)

## MCP Tools (binding)

All tools defined in `specs/24_mcp_tool_schemas.md` MUST be exposed via the MCP server.

### Tool Invocation Contract
1. Client sends `tools/call` JSON-RPC request with:
   - `name`: Tool name (e.g., `launch_run`, `get_run_status`)
   - `arguments`: Tool-specific arguments (validated against tool schema)
2. Server validates arguments against tool schema (JSON Schema validation)
3. Server executes tool and returns result or error
4. All tool executions MUST be logged to local telemetry API with:
   - `job_type = mcp_tool_call`
   - `context_json` containing tool name, arguments (redacted), result summary

### Error Handling (binding)

Tool execution errors MUST be returned as MCP error responses:
```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "error": {
    "code": <error_code>,
    "message": <error_message>,
    "data": {
      "error_code": <structured_error_code_from_specs/01>,
      "details": <additional_context>
    }
  }
}
```

Error codes follow JSON-RPC spec:
- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid request
- `-32601`: Method not found (tool not found)
- `-32602`: Invalid params (schema validation failed)
- `-32603`: Internal error (tool execution failed)

### Tool List

Minimum required tools (see `specs/24_mcp_tool_schemas.md` for full schemas):

1. **launch_run** - Start a new launch run
2. **get_run_status** - Query run status and progress
3. **list_runs** - List all runs (with filters)
4. **get_artifact** - Retrieve a run artifact by name
5. **validate_run** - Trigger validation gates on a run
6. **resume_run** - Resume a paused/failed run
7. **cancel_run** - Cancel a running launch
8. **get_telemetry** - Query telemetry for a run
9. **list_taskcards** - List available taskcards
10. **validate_taskcard** - Validate a taskcard file

## MCP Resources (optional)

Optionally, expose run artifacts as MCP resources:
- `resource://run/{run_id}/page_plan.json`
- `resource://run/{run_id}/validation_report.json`
- `resource://run/{run_id}/snapshot.json`

## MCP Implementation Best Practices (binding)

### Server Lifecycle Management
- Server MUST gracefully handle SIGTERM and SIGINT signals, completing current tool execution before shutdown
- Server MUST support concurrent tool invocations (multiple clients may call tools simultaneously)
- Server MUST use connection-scoped locks to prevent concurrent modification of the same run_id
- Server SHOULD implement request timeout (default: 300s for long-running operations like launch_run)

### Tool Argument Validation
- MUST validate all tool arguments against JSON Schema before execution
- MUST return `-32602` (Invalid params) error if validation fails, with details in error.data.details
- MUST sanitize user-provided strings (run_id, artifact names) to prevent path traversal attacks
- MUST reject run_id values that do not match pattern `^[a-zA-Z0-9_-]{8,64}$`

### Error Handling and Resilience
- Tool execution errors MUST distinguish between:
  - **Retryable errors**: Network failures, rate limits (HTTP 429), timeouts → suggest retry with exponential backoff
  - **Non-retryable errors**: Invalid arguments, schema violations, blocker issues → fail immediately
- MUST include `error_code` from specs/01_system_contract.md in error.data for structured error handling
- SHOULD log full stack traces to server-side logs but redact sensitive info from client-facing error messages
- MUST emit telemetry event `MCP_TOOL_FAILED` with error_code and tool name for all tool failures

### Security Best Practices
- MUST enforce allowed_paths for all file operations (launch_run, get_artifact)
- MUST NOT expose absolute file system paths in responses (use relative paths or run-scoped identifiers)
- MUST redact sensitive config values (API keys, tokens) from telemetry and error messages
- If exposing MCP over HTTP (optional), MUST use TLS and bearer token authentication
- MUST rate-limit tool invocations per client (default: 100 requests/minute per connection)

### Performance and Scalability
- SHOULD cache frequently accessed artifacts (page_plan.json, validation_report.json) with 60s TTL
- MUST stream large artifacts (> 1MB) rather than loading into memory
- SHOULD implement pagination for list_runs (default page size: 50)
- MUST abort tool execution if client disconnects (detect via STDIO close or HTTP connection drop)

### Observability
- MUST log all tool invocations to telemetry with:
  - Tool name, arguments (redacted), execution duration, success/failure
  - Request ID (for correlation)
  - Client identifier (if available)
- MUST expose metrics endpoint (optional) with:
  - Tool invocation counts by tool name
  - Tool execution duration histograms
  - Error rates by error_code
- SHOULD implement structured logging (JSON) for machine parsing

### Compatibility and Versioning
- Server version MUST match launcher version (e.g., `0.1.0`)
- MUST support MCP protocol version negotiation (prefer latest supported version)
- SHOULD maintain backward compatibility for deprecated tool names (e.g., `launch_start_run_from_url`)
- MUST document breaking changes in MCP tool schemas in release notes

## Acceptance
- MCP server exposes all 10 required tools
- All tools validate arguments against schemas from specs/24_mcp_tool_schemas.md
- Error responses follow JSON-RPC + MCP spec
- Tool executions are logged to telemetry
- Server passes MCP spec compliance tests (if available)
- Best practices implemented and documented
