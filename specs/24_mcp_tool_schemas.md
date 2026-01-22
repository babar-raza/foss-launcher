# MCP Tool Schemas and Error Contract

## Purpose
`specs/14_mcp_endpoints.md` lists tool names, but implementations need stable request/response shapes and a shared error model.
This document defines:
- canonical request/response payloads
- idempotency rules
- standard error codes

This document is binding.

## Conventions (binding)
- Every response MUST include `ok: true|false`.
- On success, responses MUST include `run_id` when the tool is run-scoped.
- On failure, responses MUST include `error` with the standard error shape.
- Every tool call MUST emit telemetry (see `specs/16_local_telemetry_api.md`) and MUST emit local events:
  - `WORK_ITEM_STARTED/FINISHED/FAILED` for any worker execution triggered by the tool.

## Standard error shape (binding)
```json
{
  "ok": false,
  "run_id": "optional",
  "error": {
    "code": "ILLEGAL_STATE",
    "message": "Human readable summary",
    "retryable": false,
    "details": { "any": "object" }
  }
}
```

### Error codes (minimum set)
- `INVALID_INPUT` — request missing/invalid fields
- `SCHEMA_VALIDATION_FAILED` — provided config or artifact fails schema validation
- `RUN_NOT_FOUND` — unknown run_id
- `ILLEGAL_STATE` — tool called in a state where it cannot run
- `TOOLCHAIN_MISSING` — required validator toolchain not available
- `GATE_FAILED` — validation completed but `ok=false` (returned via validation_report on success path)
- `FIX_EXHAUSTED` — max_fix_attempts reached
- `ALLOWED_PATHS_VIOLATION` — attempted writes outside allowed_paths
- `COMMIT_SERVICE_ERROR` — commit service rejected or failed
- `CANCELLED` — run cancelled
- `INTERNAL` — unexpected server error (must include details.cause_class)

## Shared types

### RunStatus
```json
{
  "run_id": "r_2026-01-21T10-00-00Z_abcd",
  "state": "VALIDATING",
  "section_states": { "products": "DONE", "docs": "DRAFTED" },
  "open_issues": [
    { "issue_id": "iss_001", "severity": "blocker", "gate": "TruthLock", "title": "Uncited claim" }
  ],
  "artifacts": [
    { "name": "page_plan.json", "sha256": "..." },
    { "name": "validation_report.json", "sha256": "..." }
  ]
}
```

### ArtifactResponse
```json
{
  "ok": true,
  "run_id": "...",
  "artifact": {
    "name": "page_plan.json",
    "content_type": "application/json",
    "sha256": "...",
    "content": "{...}"
  }
}
```

**Binding rule:** for non-text artifacts, `content` MUST be base64 and `content_type` MUST reflect it.

---

## Tool schemas (authoritative)

### launch_start_run
Start a new run from a run_config.

Request:
```json
{
  "run_config": { "...": "validated against run_config.schema.json" },
  "idempotency_key": "optional-stable-string"
}
```

Response:
```json
{
  "ok": true,
  "run_id": "r_...",
  "state": "CREATED"
}
```

Idempotency (binding):
- If `idempotency_key` is provided and a run already exists with the same key and identical run_config hash,
  the tool MUST return the existing run_id.

---

### launch_get_status
Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{ "ok": true, "status": { "...": "RunStatus" } }
```

---

### launch_get_artifact
Request:
```json
{ "run_id": "r_...", "artifact_name": "page_plan.json" }
```

Response: `ArtifactResponse`

---

### launch_validate
Runs the validator (W7) for the current worktree state.

Preconditions (binding):
- run state MUST be at least LINKING
- site worktree MUST exist for the run

Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{ "ok": true, "run_id": "r_...", "validation_report": { "...": "validation_report.schema.json" } }
```

Notes:
- `ok=true` here means the tool executed successfully; gate pass/fail is expressed inside `validation_report.ok`.

---

### launch_fix_next
Selects the next fixable issue deterministically and applies a fix attempt (W8), then re-validates (W7).

Preconditions (binding):
- run state MUST be VALIDATING
- last validation_report MUST exist and have `ok=false`

Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{
  "ok": true,
  "run_id": "r_...",
  "fixed_issue_id": "iss_001",
  "applied_patch_ids": ["patch_007"],
  "remaining_blockers": 2,
  "validation_report": { "...": "latest report" }
}
```

Stop behavior (binding):
- If max_fix_attempts reached, respond with `ok=false` and `error.code=FIX_EXHAUSTED`.

---

### launch_resume
Resumes a paused/partial run from snapshot and continues until the next stable boundary (typically the next state transition).

Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{ "ok": true, "status": { "...": "RunStatus" } }
```

---

### launch_cancel
Cancels a run.

Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{ "ok": true, "run_id": "r_...", "cancelled": true, "state": "CANCELLED" }
```

---

### launch_open_pr
Opens a PR using the commit service.

Preconditions (binding):
- run state MUST be READY_FOR_PR
- last validation_report MUST have `ok=true`

Request:
```json
{ "run_id": "r_..." }
```

Response:
```json
{
  "ok": true,
  "run_id": "r_...",
  "pr_url": "...",
  "branch": "launch/r_.../product_slug",
  "commit_sha": "..."
}
```

---

### launch_list_runs
Request:
```json
{ "filter": { "product_slug": "optional", "state": "optional" } }
```

Response:
```json
{
  "ok": true,
  "runs": [
    { "run_id": "r_...", "product_slug": "...", "state": "DONE", "started_at": "...", "finished_at": "..." }
  ]
}
```

## Acceptance
- A client can implement MCP calls without reverse engineering.
- Error codes are consistent, retryable is meaningful, and illegal state is enforced.
- All tools can be traced end-to-end in telemetry using run_id + trace/span ids.
