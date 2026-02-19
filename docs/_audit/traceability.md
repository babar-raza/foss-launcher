# Traceability (Code ? Docs)

Feature list is derived from code surfaces (CLI, MCP tools, modules, schemas). Each row maps feature ? evidence ? current docs coverage ? gaps.

Last updated: 2026-02-19  
Audit mode: Maintenance (delta scan)

| Feature | Evidence (code) | Current docs coverage | Gaps |
|---------|-----------------|----------------------|------|
| CLI: `launch run` | `src/launch/cli/main.py` | `docs/reference/cli_usage.md` (runbook) | Docs mention `--dry-run` and `--verbose` as "if implemented"; code implements both. No gap noted here. |
| CLI: `launch status` | `src/launch/cli/main.py` | `docs/reference/cli_usage.md` (status section) | Coverage exists but verify status output format matches code. |
| CLI: `launch list` | `src/launch/cli/main.py` | `docs/reference/cli_usage.md` (list section) | Coverage exists but verify list output format matches code. |
| CLI: `launch cancel` | `src/launch/cli/main.py` | `docs/reference/cli_usage.md` (cancel section) | Coverage exists but verify cancel behavior matches code. |
| CLI: `launch validate <run_id>` | `src/launch/cli/main.py` | `docs/reference/cli_usage.md` (validation runbook) | Docs use `launch_validate --run_dir ...` (validator CLI), not `launch validate <run_id>` (launch CLI). Needs reconciliation. |
| Console scripts: `launch_run`, `launch_validate`, `launch_mcp` | `pyproject.toml` | `docs/reference/cli_usage.md` | `launch_validate` CLI in code takes positional `run_dir` (Typer), docs show `--run_dir` flag and `--config` usage which are not implemented in `src/launch/validators/cli.py`. |
| Validator scaffold gates | `src/launch/validators/cli.py` | `docs/reference/cli_usage.md` (gate runbook), specs: `specs/09_validation_gates.md` | Gates 0-3 implemented (run_layout, toolchain_lock, run_config_schema, schema_validation). Gates 4-13 marked NOT_IMPLEMENTED (blocker in prod profile per Guarantee E). Docs/specs should reflect this split. |
| MCP server (`launch_mcp serve`) | `src/launch/mcp/server.py` | `docs/reference/cli_usage.md` (MCP runbook) | Code exposes only `serve` subcommand; docs mention host/port flags not present. |
| MCP tool catalog | `src/launch/mcp/tools.py`, `src/launch/mcp/handlers.py` | Specs: `specs/14_mcp_endpoints.md`, `specs/24_mcp_tool_schemas.md` | **IMPLEMENTATION STATUS**:<br>- `launch_start_run`: Creates run directory, returns run_id (non-blocking).<br>- `launch_get_status`: Reads snapshot/events, returns RunStatus.<br>- `launch_list_runs`: Lists runs with optional filtering.<br>- `launch_get_artifact`: Retrieves artifact with SHA256.<br>- `launch_validate`: Returns stub (W7 blocked by TC-470).<br>- `launch_fix_next`: Returns "not yet implemented" (W8 blocked by TC-480).<br>- `launch_resume`: Returns current status (resume logic not implemented).<br>- `launch_cancel`: Returns "not yet implemented".<br>- `launch_open_pr`: Returns "not yet implemented" (TC-490 blocked).<br>- `launch_start_run_from_product_url`: Returns "not yet implemented" (TC-520 blocked).<br>- `launch_start_run_from_github_repo_url`: Returns "not yet implemented" (TC-520 blocked).<br>- `get_run_telemetry`: Reads events.ndjson, returns telemetry summary. |
| Orchestrator graph (single-run) | `src/launch/orchestrator/graph.py`, `src/launch/orchestrator/run_loop.py` | `docs/reference/architecture.md`, specs: `specs/11_state_and_events.md`, `specs/28_coordination_and_handoffs.md` | Batch execution is blocked in code (`execute_batch` NotImplemented). Docs/specs should flag the block clearly. |
| Worker pipeline W1–W11 | `src/launch/workers/*/worker.py` | Specs: `specs/21_worker_contracts.md` | Verify docs/architecture claims of "scaffold only" vs implemented worker modules. |
| Run layout (RUN_DIR) | `src/launch/io/run_layout.py` | Specs: `specs/29_project_repo_structure.md`, `docs/reference/architecture.md` | No gap verified; coverage not validated against code. |
| Telemetry API endpoints | `src/launch/telemetry_api/routes/*.py`, `src/launch/telemetry_api/server.py` | `docs/reference/local-telemetry-api.md`, `docs/reference/local-telemetry.md`, specs: `specs/16_local_telemetry_api.md` | No gap verified; coverage not validated against code. |
| Telemetry client outbox buffering | `src/launch/clients/telemetry.py` | `docs/reference/architecture.md` | ROOT ORPHAN doc; verify dedicated operator docs for outbox behavior. |
| Network allowlist enforcement | `src/launch/clients/http.py`, `config/network_allowlist.yaml` | No matches in `docs/` | Add operator/config documentation for allowlist usage and format. |
| Commit service integration | `src/launch/clients/commit_service.py`, `src/launch/workers/w11_pr_manager/worker.py` | Specs: `specs/17_github_commit_service.md`, `specs/12_pr_and_release.md` | No gap verified; coverage not validated against code. |
| Security gate (secrets scanning) | `src/launch/validators/security_gate.py`, `src/launch/security/*` | Specs: `specs/34_strict_compliance_guarantees.md`, `specs/09_validation_gates.md` | No user-facing docs found in `docs/`. Consider adding operator guidance. |
| Run config schema | `specs/schemas/run_config.schema.json`, `src/launch/io/run_config.py` | Specs schema + `docs/reference/cli_usage.md` references | Docs reference run_config but do not enumerate schema; consider linking to schema or generating reference. |
| **NEW: skip_sections config** | `specs/schemas/run_config.schema.json` (line 126-139) | Not documented in `docs/reference/config.md` | Add `skip_sections` to config reference with examples. |
| **NEW: allow_manual_edits config** | `specs/schemas/run_config.schema.json` (line 432-436) | Not documented in `docs/reference/config.md` | Add `allow_manual_edits` to config reference (emergency escape hatch). |
| **NEW: seo_enabled config** | `specs/schemas/run_config.schema.json` (line 442-446) | Not documented in `docs/reference/config.md` | Add `seo_enabled` to config reference (W6 SEO Optimizer toggle). |
| **NEW: taskcard_id config** | `specs/schemas/run_config.schema.json` (line 447-451) | Not documented in `docs/reference/config.md` | Add `taskcard_id` to config reference (write fence policy). |
| **NEW: ingestion config block** | `specs/schemas/run_config.schema.json` (line 553-593) | Not documented in `docs/reference/config.md` | Add `ingestion` block to config reference (scan_directories, exclude_patterns, gitignore_mode, example_directories, record_binary_files, detect_phantom_paths). |
| AI Governance Rules | `docs/guides/ai-governance.md` (moved from root) | `docs/guides/ai-governance.md` | Document moved from `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` to canonical location. |
| Taskcard Creation Workflow | `docs/guides/creating-taskcards.md` (moved from root) | `docs/guides/creating-taskcards.md` | Document moved from `docs/creating_taskcards.md` to canonical location. |
| LLM Model Reference | `docs/reference/llm-models.md` (moved from root) | `docs/reference/llm-models.md` | Document moved from `docs/MODEL_REFERENCE.md` to canonical location. |
| Telemetry Integration Report | `docs/_archive/telemetry_integration_20260208.md` (archived) | `docs/_archive/telemetry_integration_20260208.md` | Historical completion report archived. May contain useful lessons for future integrations. |

## Root Orphan Check (docs/ root, maxdepth=1)

| Path | Status | Action |
|------|--------|--------|
| `docs/README.md` | Allowed | Project docs home |
| `docs/_audit/` | Allowed | Audit outputs |
| `docs/_archive/` | Allowed | Archived docs |
| `docs/overview/` | Allowed | IA category |
| `docs/getting-started/` | Allowed | IA category |
| `docs/guides/` | Allowed | IA category |
| `docs/reference/` | Allowed | IA category |
| `docs/architecture/` | Allowed | IA category |
| `docs/operations/` | Allowed | IA category |
| `docs/development/` | Allowed | IA category |

**Result**: No root orphans detected. All files under `docs/` root are either `README.md` or allowed meta folders/IA categories.
