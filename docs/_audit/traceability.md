# Traceability (Code ? Docs)

Feature list is derived from code surfaces (CLI, MCP tools, modules, schemas). Each row maps feature ? evidence ? current docs coverage ? gaps.

| Feature | Evidence (code) | Current docs coverage | Gaps |
| --- | --- | --- | --- |
| CLI: `launch run` | `src/launch/cli/main.py` | `docs/cli_usage.md` (runbook) | Docs mention `--dry-run` and `--verbose` as “if implemented”; code implements both. No gap noted here. |
| CLI: `launch status` / `launch list` / `launch cancel` | `src/launch/cli/main.py` | No matches in `docs/cli_usage.md` (rg search) | Missing runbooks for status/list/cancel. |
| CLI: `launch validate <run_id>` | `src/launch/cli/main.py` | `docs/cli_usage.md` (validation runbook) | Docs use `launch_validate --run_dir ...` (validator CLI), not `launch validate <run_id>` (launch CLI). Needs reconciliation. |
| Console scripts: `launch_run`, `launch_validate`, `launch_mcp` | `pyproject.toml` | `docs/cli_usage.md` | `launch_validate` CLI in code takes positional `run_dir` (Typer), docs show `--run_dir` flag and `--config` usage which are not implemented in `src/launch/validators/cli.py`. |
| Validator scaffold gates | `src/launch/validators/cli.py` | `docs/cli_usage.md` (gate runbook), specs: `specs/09_validation_gates.md` | Many gates are NOT_IMPLEMENTED in code; docs/specs may describe full gate set. Ensure docs reflect scaffold behavior and prod-blocking behavior. |
| MCP server (`launch_mcp serve`) | `src/launch/mcp/server.py` | `docs/cli_usage.md` (MCP runbook) | Code exposes only `serve` subcommand; docs mention host/port flags not present. |
| MCP tool catalog | `src/launch/mcp/tools.py`, `src/launch/mcp/handlers.py` | Specs: `specs/14_mcp_endpoints.md`, `specs/24_mcp_tool_schemas.md` | `launch_start_run_from_github_repo_url` handler returns “not yet implemented” error; docs/specs should note this gap. |
| Orchestrator graph (single-run) | `src/launch/orchestrator/graph.py`, `src/launch/orchestrator/run_loop.py` | `docs/architecture.md`, specs: `specs/11_state_and_events.md`, `specs/28_coordination_and_handoffs.md` | Batch execution is blocked in code (`execute_batch` NotImplemented). Docs/specs should flag the block clearly. |
| Worker pipeline W1–W9 | `src/launch/workers/*/worker.py` | Specs: `specs/21_worker_contracts.md` | Verify docs/architecture claims of “scaffold only” vs implemented worker modules. |
| Run layout (RUN_DIR) | `src/launch/io/run_layout.py` | Specs: `specs/29_project_repo_structure.md`, `docs/architecture.md` | Docs/architecture is a ROOT ORPHAN; ensure canonical placement. |
| Telemetry API endpoints | `src/launch/telemetry_api/routes/*.py`, `src/launch/telemetry_api/server.py` | `docs/reference/local-telemetry-api.md`, `docs/reference/local-telemetry.md`, specs: `specs/16_local_telemetry_api.md` | No gap verified; coverage not validated against code. |
| Telemetry client outbox buffering | `src/launch/clients/telemetry.py` | `docs/architecture.md` | ROOT ORPHAN doc; verify dedicated operator docs for outbox behavior. |
| Network allowlist enforcement | `src/launch/clients/http.py`, `config/network_allowlist.yaml` | No matches in `docs/` | Add operator/config documentation for allowlist usage and format. |
| Commit service integration | `src/launch/clients/commit_service.py`, `src/launch/workers/w9_pr_manager/worker.py` | Specs: `specs/17_github_commit_service.md`, `specs/12_pr_and_release.md` | No gap verified; coverage not validated against code. |
| Security gate (secrets scanning) | `src/launch/validators/security_gate.py`, `src/launch/security/*` | Specs: `specs/34_strict_compliance_guarantees.md`, `specs/09_validation_gates.md` | No user-facing docs found in `docs/`. Consider adding operator guidance. |
| Run config schema | `specs/schemas/run_config.schema.json`, `src/launch/io/run_config.py` | Specs schema + `docs/cli_usage.md` references | Docs reference run_config but do not enumerate schema; consider linking to schema or generating reference. |
