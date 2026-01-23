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
