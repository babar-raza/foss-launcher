# System Audit (Code-First)

> Scope: This audit treats the codebase as source of truth. Claims below are backed by code evidence (file paths).

## Product / System Purpose (from code)
- A Typer-based CLI provides a “FOSS Launcher - Automated documentation generation system” entrypoint, including run creation, status, validation, and cancellation. Evidence: `src/launch/cli/main.py`.
- A single-run orchestrator creates RUN_DIR structure, emits events, replays snapshots, and executes a LangGraph-based workflow that invokes workers. Evidence: `src/launch/orchestrator/run_loop.py`, `src/launch/orchestrator/graph.py`, `src/launch/state/event_log.py`, `src/launch/state/snapshot_manager.py`.
- Worker implementations produce artifacts such as repo inventory, facts, snippets, page plans, drafts, patch bundles, validation reports, and PR metadata. Evidence: `src/launch/workers/**/worker.py` (W1–W9 docstrings and artifact writers).
- PR creation is delegated to a commit service client rather than direct git operations. Evidence: `src/launch/clients/commit_service.py`, `src/launch/workers/w9_pr_manager/worker.py`.

## Component Map (modules ? responsibilities)
- CLI
  - `src/launch/cli/main.py`: `launch` command group with `run`, `status`, `list`, `validate`, `cancel`.
  - `src/launch/cli.py`: console script entrypoint wrapper.
- Orchestrator
  - `src/launch/orchestrator/graph.py`: LangGraph state machine with nodes for clone ? ingest ? facts ? plan ? draft ? patch ? validate ? fix ? PR.
  - `src/launch/orchestrator/run_loop.py`: run execution, event emission, snapshot replay, exit codes, batch execution blocked.
  - `src/launch/orchestrator/worker_invoker.py`: worker invocation (used by graph nodes).
- Workers (integrators)
  - W1 RepoScout: clone + fingerprint + doc/example discovery ? repo_inventory/discovered_docs/discovered_examples. Evidence: `src/launch/workers/w1_repo_scout/worker.py`.
  - W2 FactsBuilder: claims extraction + evidence mapping + contradiction resolution ? product_facts/evidence_map. Evidence: `src/launch/workers/w2_facts_builder/worker.py`.
  - W3 SnippetCurator: doc/code snippet extraction ? snippet_catalog. Evidence: `src/launch/workers/w3_snippet_curator/worker.py`.
  - W4 IAPlanner: page plan generation. Evidence: `src/launch/workers/w4_ia_planner/worker.py`.
  - W5 SectionWriter: draft section markdown + manifest. Evidence: `src/launch/workers/w5_section_writer/worker.py`.
  - W6 LinkerAndPatcher: patch bundle + diff report + apply patches. Evidence: `src/launch/workers/w6_linker_and_patcher/worker.py`.
  - W7 Validator: gate execution + validation report. Evidence: `src/launch/workers/w7_validator/worker.py`.
  - W8 Fixer: deterministic single-issue fixes. Evidence: `src/launch/workers/w8_fixer/worker.py`.
  - W9 PRManager: commit service integration + PR metadata. Evidence: `src/launch/workers/w9_pr_manager/worker.py`.
- MCP Server
  - `src/launch/mcp/server.py`: STDIO JSON-RPC MCP server (`launch_mcp`).
  - `src/launch/mcp/tools.py`: tool schemas + handler registry.
  - `src/launch/mcp/handlers.py`: handler implementations (orchestrator-integrated).
- Telemetry API
  - `src/launch/telemetry_api/server.py`: FastAPI server + env-based configuration.
  - `src/launch/telemetry_api/routes/*.py`: endpoints for runs, batch uploads, metadata, metrics.
- IO & Models
  - `src/launch/io/run_layout.py`: RUN_DIR layout + required paths.
  - `src/launch/io/run_config.py`: run_config load + schema validation.
  - `src/launch/io/schema_validation.py`: JSON Schema validation.
  - `src/launch/models/*`: event, state, run_config, product_facts models.
- Security & Compliance
  - `src/launch/security/*`: secret detection + redaction + file scanning.
  - `src/launch/clients/http.py`: network allowlist enforcement.
- Observability
  - `src/launch/observability/run_summary.py`: run summary report generation.
  - `src/launch/observability/reports_index.py`: report index generation.
  - `src/launch/observability/evidence_packager.py`: evidence ZIP + manifest.

## Key Workflows (step-by-step with evidence)
### A) CLI “run” workflow (single-run)
1. `launch run --config <path>` loads and schema-validates run_config. Evidence: `src/launch/cli/main.py`, `src/launch/io/run_config.py`, `specs/schemas/run_config.schema.json`.
2. RUN_DIR is created and populated with required files and folders. Evidence: `src/launch/cli/main.py`, `src/launch/io/run_layout.py`.
3. Orchestrator executes a single run (graph streaming). Evidence: `src/launch/orchestrator/run_loop.py`.
4. Orchestrator graph invokes workers in sequence. Evidence: `src/launch/orchestrator/graph.py`.
5. Events appended to `events.ndjson`; snapshot replay ensures state = f(events). Evidence: `src/launch/state/event_log.py`, `src/launch/state/snapshot_manager.py`.
6. Validation gates are invoked by W7 and/or `launch_validate` scaffold. Evidence: `src/launch/workers/w7_validator/worker.py`, `src/launch/validators/cli.py`.
7. PR creation uses commit service client and writes `pr.json`. Evidence: `src/launch/workers/w9_pr_manager/worker.py`, `src/launch/clients/commit_service.py`.

### B) MCP tool workflow (STDIO)
1. MCP server runs on STDIO with registered tools. Evidence: `src/launch/mcp/server.py`, `src/launch/mcp/tools.py`.
2. Tool calls route to handlers that create runs, read status, fetch artifacts, validate, fix, resume, cancel, open PR. Evidence: `src/launch/mcp/handlers.py`.

### C) Local Telemetry API workflow
1. FastAPI server exposes `/api/v1/runs`, `/api/v1/runs/{run_id}/events`, `/api/v1/runs/{event_id}/associate-commit`, and batch upload endpoints. Evidence: `src/launch/telemetry_api/routes/runs.py`, `src/launch/telemetry_api/routes/batch.py`.
2. Metadata/metrics endpoints are exposed. Evidence: `src/launch/telemetry_api/routes/metadata.py`.
3. Server configuration supports env overrides for host/port/db path. Evidence: `src/launch/telemetry_api/server.py`.

## Config Reference (keys, defaults, validation)
### Run Config (validated)
- Loaded by: `load_and_validate_run_config(repo_root, config_path)` in `src/launch/io/run_config.py`.
- Schema source: `specs/schemas/run_config.schema.json` (JSON Schema Draft 2020-12).
- Required keys (non-exhaustive list with defaults):
  - `schema_version`, `product_slug`, `product_name`, `family`, `github_repo_url`, `github_ref` (40-char SHA), `required_sections`, `site_layout`, `allowed_paths`, `llm`, `mcp`, `telemetry`, `commit_service`, `templates_version`, `ruleset_version`, `allow_inference`, `max_fix_attempts`, `budgets`. Evidence: `specs/schemas/run_config.schema.json`.
  - `locale` (default `en`) or `locales` (array); `layout_mode` (default `auto`); `validation_profile` (default `local`); `ci_strictness` (default `strict`). Evidence: `specs/schemas/run_config.schema.json`.
  - `site_layout` contains `content_root` (default `content`), `subdomain_roots` defaults, `localization.mode_by_section`, and `path_patterns.by_section`. Evidence: `specs/schemas/run_config.schema.json`.
  - `llm` block: `api_base_url`, `model`, `decoding` and optional `api_key_env`, `request_timeout_s` (default 120), `max_concurrency` (default 4). Evidence: `specs/schemas/run_config.schema.json`.
  - `mcp` block: `enabled` (default true), `listen_host` (default 127.0.0.1), `listen_port` (default 8787), `auth_token_env`. Evidence: `specs/schemas/run_config.schema.json`.
  - `telemetry` block: `endpoint_url`, `project`, `run_tags`, `auth_token_env`. Evidence: `specs/schemas/run_config.schema.json`.
  - `commit_service` block: `endpoint_url`, `github_token_env`, `commit_message_template`, `commit_body_template`, optional author fields. Evidence: `specs/schemas/run_config.schema.json`.
  - `budgets` block: `max_runtime_s`, `max_llm_calls`, `max_llm_tokens`, `max_file_writes`, `max_patch_attempts`, `max_lines_per_file` (default 500), `max_files_changed` (default 100). Evidence: `specs/schemas/run_config.schema.json`.

### Toolchain Lock
- Loaded by: `load_toolchain_lock()` in `src/launch/io/toolchain.py`.
- File: `config/toolchain.lock.yaml` (PIN_ME sentinel detection). Evidence: `src/launch/io/toolchain.py`.

### Network Allowlist
- Loaded by: `_load_allowlist()` in `src/launch/clients/http.py`.
- File: `config/network_allowlist.yaml`. Evidence: `src/launch/clients/http.py`.

### Telemetry API Server (env)
- Environment variables: `TELEMETRY_API_HOST`, `TELEMETRY_API_PORT`, `TELEMETRY_LOG_LEVEL`, `TELEMETRY_DB_PATH`. Evidence: `src/launch/telemetry_api/server.py`.

## CLI / API Reference (from code)
### Console scripts (pyproject)
- `launch_run` ? `launch.cli:main` (CLI commands below). Evidence: `pyproject.toml`.
- `launch_validate` ? `launch.validators.cli:main`. Evidence: `pyproject.toml`, `src/launch/validators/cli.py`.
- `launch_mcp` ? `launch.mcp.server:main`. Evidence: `pyproject.toml`, `src/launch/mcp/server.py`.

### `launch` commands (Typer)
- `launch run --config <path> [--run_dir <path>] [--dry-run] [--verbose|-v]`. Evidence: `src/launch/cli/main.py`.
- `launch status <run_id> [--verbose|-v]`. Evidence: `src/launch/cli/main.py`.
- `launch list [--limit|-n <int>] [--all|-a]`. Evidence: `src/launch/cli/main.py`.
- `launch validate <run_id> [--profile local|ci|prod]`. Evidence: `src/launch/cli/main.py`.
- `launch cancel <run_id> [--force]`. Evidence: `src/launch/cli/main.py`.

### `launch_validate` (validator scaffold)
- `launch_validate <run_dir> [--profile local|ci|prod]`. Evidence: `src/launch/validators/cli.py`.

### `launch_mcp`
- `launch_mcp serve` only; server listens on STDIO. Evidence: `src/launch/mcp/server.py`.

### MCP tool catalog
- Tool schemas + handlers registered for: `launch_start_run`, `launch_get_status`, `launch_list_runs`, `launch_get_artifact`, `launch_validate`, `launch_cancel`, `launch_resume`, `launch_fix_next`, `launch_open_pr`, `launch_start_run_from_product_url`, `launch_start_run_from_github_repo_url`, `get_run_telemetry`. Evidence: `src/launch/mcp/tools.py`, `src/launch/mcp/handlers.py`.

### Telemetry API endpoints
- Runs: `POST /api/v1/runs`, `GET /api/v1/runs`, `GET /api/v1/runs/{run_id}`, `PATCH /api/v1/runs/{event_id}`, `GET /api/v1/runs/{run_id}/events`, `POST /api/v1/runs/{event_id}/associate-commit`. Evidence: `src/launch/telemetry_api/routes/runs.py`.
- Batch: `POST /api/v1/runs/batch`, `POST /api/v1/runs/batch-transactional`. Evidence: `src/launch/telemetry_api/routes/batch.py`.
- Metadata/Metrics: `GET /api/v1/metadata`, `GET /metrics`. Evidence: `src/launch/telemetry_api/routes/metadata.py`.

## Data Directories & File Contracts
- RUN_DIR layout and required paths: `events.ndjson`, `snapshot.json`, `telemetry_outbox.jsonl`, `work/` (repo/site/workflows), `artifacts/`, `logs/`, `reports/`, `drafts/{products,docs,reference,kb,blog}`. Evidence: `src/launch/io/run_layout.py`.
- Telemetry database default path: `./telemetry.db` (SQLite). Evidence: `src/launch/telemetry_api/server.py`.
- Evidence package ZIP includes artifacts, reports, events, snapshot, run_config. Evidence: `src/launch/observability/evidence_packager.py`.

## Observability (logs/telemetry/metrics)
- Structured logging via `structlog` configured in `src/launch/util/logging.py`.
- Local event log and snapshot for replay/audit: `events.ndjson`, `snapshot.json`. Evidence: `src/launch/state/event_log.py`, `src/launch/state/snapshot_manager.py`.
- Telemetry client writes to API or buffers to `RUN_DIR/telemetry_outbox.jsonl`. Evidence: `src/launch/clients/telemetry.py`, `src/launch/io/run_layout.py`.
- Run summary and reports index generators: `src/launch/observability/run_summary.py`, `src/launch/observability/reports_index.py`.

## Testing Strategy (what exists + how to run)
- Test runner: `pytest` (via Makefile and pyproject). Evidence: `Makefile`, `pyproject.toml`.
- Test locations: `tests/unit/**`, `tests/e2e/**`. Evidence: `pyproject.toml`, `tests/` tree.
- Example tests: `tests/unit/test_tc_530_entrypoints.py`, `tests/e2e/test_tc_522_pilot_cli.py`. Evidence: `tests/` tree.

## Known Gaps / Risks (code-evidenced)
- Batch execution is explicitly blocked and raises `NotImplementedError` (single-run only). Evidence: `src/launch/orchestrator/run_loop.py`.
- `launch_validate` is a scaffold: multiple gates are marked NOT_IMPLEMENTED and always fail in prod profile. Evidence: `src/launch/validators/cli.py`.
- MCP `launch_start_run` handler does not validate run_config schema (TODO). Evidence: `src/launch/mcp/handlers.py`.
- MCP `launch_start_run_from_github_repo_url` returns an error (“not yet implemented”). Evidence: `src/launch/mcp/handlers.py`.
