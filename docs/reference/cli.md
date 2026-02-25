# CLI Reference

**Canonical Source**: This is the authoritative reference for the `launch` CLI.

**Source Code**: [`src/launch/cli/main.py`](../src/launch/cli/main.py)

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Commands](#commands)
4. [Exit Codes](#exit-codes)
5. [Environment Variables](#environment-variables)

---

> **Incremental Debugging**: Use `launch resume` to re-enter the pipeline at any worker
> without re-running the full 60–90 min pipeline from W1. See [Resumable Pipeline spec](../specs/43_resumable_pipeline.md).

---

## Overview

The `launch` CLI provides commands for:

- Starting documentation generation runs
- **Resuming runs from any worker** (incremental debugging)
- **Running bounded phases** with verification (phased execution)
- **Monitoring runs in real-time** (event tailing)
- Checking run status
- Listing runs
- Running validation gates
- Cancelling runs
- Starting MCP server

**Console Scripts** (installed via `pyproject.toml`):

| Script | Purpose |
|--------|---------|
| `launch_run` | Main orchestration runner (alias for `launch run`) |
| `launch_validate` | Validation and gate runner (alias for `launch validate`) |
| `launch_mcp` | MCP server for Claude Desktop integration |

---

## Installation

### With uv (Recommended)

```bash
uv sync
```

### With pip (Fallback)

```bash
python -m pip install -e ".[dev]"
```

### Verification

```bash
launch_run --help
launch_validate --help
launch_mcp --help
```

If console scripts are not in PATH, invoke directly:

```bash
python -c "from launch.cli import main; main()" --help
python -c "from launch.validators.cli import main; main()" --help
python -c "from launch.mcp.server import main; main()" --help
```

---

## Commands

### `launch run`

Start a new documentation generation run.

```bash
launch run --config <path_to_config.yaml> [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to run_config YAML (required) |
| `--run_dir PATH` | Target RUN_DIR (runs/<run_id>) |
| `--dry-run` | Validate config without executing |
| `--verbose`, `-v` | Increase logging verbosity |

#### Example

```bash
launch run --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Validation failure |
| `2` | Execution failure |

---

### `launch resume`

Resume a pipeline run from a specific worker, reusing artifacts already produced by a previous run.
This is the primary tool for **incremental debugging** — if a bug is in W5, skip W1–W4 entirely.

```bash
launch resume --run-dir <path> --from-worker <alias> [--verbose]
```

#### Options

| Flag | Description |
|------|-------------|
| `--run-dir PATH` | Existing run directory (`runs/<run_id>/`) — **required** |
| `--from-worker ALIAS` | Worker to resume from (short alias or full node name) — **required** |
| `--verbose`, `-v` | Increase logging verbosity |

#### Worker Aliases

| Short | Full node name | Skips workers |
|-------|---------------|---------------|
| `W1` | `clone_inputs` | (none — starts from beginning) |
| `W2` | `ingest` | W1 |
| `W3` | `build_facts` | W1–W2 |
| `W4` | `plan_pages` | W1–W3 |
| `W5` | `draft_sections` | W1–W4 |
| `W6` | `optimize_seo` | W1–W5 |
| `W7` | `review_content` | W1–W6 |
| `W8` | `link_and_patch` | W1–W7 |
| `W9` | `validate` | W1–W8 |
| `W10` | `fix` | W1–W9 |
| `W11` | `open_pr` | W1–W10 |

#### Examples

```bash
# Resume from W5 (SectionWriter) using the most recent run
launch resume --run-dir runs/r_20260221T123456Z_... --from-worker W5

# Using the full node name
launch resume --run-dir runs/r_20260221T... --from-worker draft_sections

# Resume from W9 (Validator) to re-run validation only
launch resume --run-dir runs/r_20260221T... --from-worker W9 --verbose
```

Via `run_pilot.py` (auto-discovers most recent run):

```bash
# Resume pilot from W5 without specifying run_dir manually
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
    --pilot pilot-aspose-3d-foss-python --from-worker W5
```

#### Behaviour

- Artifacts from `--from-worker` onward are **overwritten**; earlier artifacts are **preserved**
- `events.ndjson` is **appended** (never reset); a `RUN_RESUMED` event is written before graph starts
- `run_config.yaml` is loaded from `--run-dir` (no `--config` flag needed)
- Required artifacts are validated before the graph starts; all missing paths are reported at once
- `--run-dir` must be under the configured `runs/` root (path-traversal guard)

#### Required Artifacts Per Entry Point

| From | Must exist in `run_dir/` |
|------|--------------------------|
| `W1` | (none) |
| `W2` | `work/repo/` directory |
| `W3` | `artifacts/repo_inventory.json`, `artifacts/frontmatter_contract.json` |
| `W4` | + `artifacts/product_facts.json`, `artifacts/snippet_catalog.json` |
| `W5` | + `artifacts/page_plan.json` |
| `W6`–`W8` | + `artifacts/draft_manifest.json`, `artifacts/seo_report.json` |
| `W9` | + `artifacts/patch_bundle.json` |
| `W10` | + `artifacts/validation_report.json` |
| `W11` | + `artifacts/patch_bundle.json` |

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Run completed (check run state for content pass/fail) |
| `1` | Validation failure (unknown alias, missing run_config, missing artifacts) |
| `2` | Execution failure (runtime error during graph streaming) |

---

### `launch phase`

Run a bounded set of pipeline phases with optional verification. Phases group workers
into logical stages, enabling incremental execution and artifact inspection between stages.

```bash
launch phase --config <path_to_config.yaml> [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to run_config YAML file (required) |
| `--phase-start ID` | First phase to execute (default: `P1`) |
| `--phase-end ID` | Last phase to execute (default: `P6`) |
| `--verify-only` | Skip execution, only verify artifacts for the phase range |
| `--run-dir PATH` | Existing run directory (required for `--verify-only` and for resuming later phases) |
| `--verbose`, `-v` | Increase logging verbosity |
| `--live` | Show real-time event progress during execution |
| `--pause` | Pause after each phase for inspection (implies `--live`). Press Enter to continue, `q` to stop |

#### Phase Groups

| Phase | Workers | Description |
|-------|---------|-------------|
| `P1` | W1, W2 | Repo ingestion + facts |
| `P2` | W3, W4 | Snippets + page planning |
| `P3` | W5, W6 | Drafting + SEO |
| `P4` | W7, W8 | Review + linking |
| `P5` | W9, W10 | Validation + fixing |
| `P6` | W11 | PR/packaging |

#### Examples

```bash
# Run all phases from scratch
launch phase --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml

# Run only ingestion and planning phases
launch phase --config run_config.pinned.yaml --phase-start P1 --phase-end P2

# Resume from drafting through validation on an existing run
launch phase --config run_config.pinned.yaml --phase-start P3 --phase-end P5 \
    --run-dir runs/r_20260225T...

# Verify artifacts without re-executing
launch phase --config run_config.pinned.yaml --verify-only \
    --run-dir runs/r_20260225T... --phase-start P1 --phase-end P2

# Interactive mode: pause between phases for inspection
launch phase --config run_config.pinned.yaml --phase-start P1 --phase-end P3 --pause
```

#### Behaviour

- Each phase executes its workers sequentially via `launch resume` under the hood
- After execution, artifacts for all executed phases are verified (schema + existence checks)
- `--verify-only` skips execution entirely and only checks artifacts
- `--pause` mode runs one phase at a time, displays verification results, and waits for user input
- A fresh run (no `--run-dir`) creates a new `RUN_DIR` automatically
- Resuming later phases requires `--run-dir` pointing to an existing run

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All phases pass (execution + verification) |
| `1` | Validation/argument failure or verification failure |
| `2` | Execution failure |

---

### `launch monitor`

Tail events from a run directory in real-time. Replays all existing events, then
continues tailing for new ones. Useful for monitoring a run started in another terminal
or for inspecting events from a completed run.

```bash
launch monitor --run-dir <path> [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--run-dir PATH` | Run directory to monitor (`runs/<run_id>/`) — **required** |
| `--verbose`, `-v` | Show LLM call events (normally suppressed) |

#### Event Types Displayed

| Event | Display |
|-------|---------|
| `RUN_CREATED` | Run ID |
| `RUN_RESUMED` | Run ID |
| `PHASE_STARTED` | Phase ID + worker list (as a rule separator) |
| `PHASE_COMPLETED` | Phase ID + PASS/FAIL |
| `WORK_ITEM_STARTED` | Worker name |
| `WORK_ITEM_FINISHED` | Worker name + OK/FAIL |
| `ARTIFACT_WRITTEN` | Artifact name |
| `RUN_STATE_CHANGED` | Old state -> New state |
| `GATE_RUN_FINISHED` | Gate ID + PASS/FAIL |
| `RUN_COMPLETED` | Completion marker |
| `RUN_FAILED` | Failure reason |
| `LLM_CALL_*` | LLM call details (verbose mode only) |

#### Examples

```bash
# Monitor a running pipeline in another terminal
launch monitor --run-dir runs/r_20260225T115014Z

# Inspect a completed run's events with LLM call details
launch monitor --run-dir runs/r_20260225T115014Z --verbose
```

#### Behaviour

- Replays all existing events from `events.ndjson` first (catch-up display)
- Then polls for new events every 0.5 seconds
- Press `Ctrl+C` to stop monitoring
- Safe on Windows NTFS — no file locking conflicts with concurrent writers
- If `events.ndjson` doesn't exist yet, waits for the file to appear

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Stopped by user (`Ctrl+C`) |
| `1` | Invalid run directory |

---

### `launch status`

Check run status.

```bash
launch status <run_id> [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--verbose`, `-v` | Show detailed information |

#### Example

```bash
launch status aspose-note-foss-python-main-20260128
```

---

### `launch list`

List all runs.

```bash
launch list [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--limit N`, `-n N` | Maximum number of runs to show (default: 20) |
| `--all`, `-a` | Show all runs (ignore limit) |

#### Example

```bash
launch list
launch list --limit 50
launch list --all
```

---

### `launch validate`

Run validation gates on a run.

```bash
launch validate <run_id> --profile <profile>
```

#### Options

| Flag | Description |
|------|-------------|
| `--profile` | Validation profile: local, ci, prod (default: local) |

#### Example

```bash
launch validate aspose-note-foss-python-main-20260128 --profile ci
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All gates pass |
| `1` | One or more gates fail |

---

### `launch cancel`

Cancel a running task.

```bash
launch cancel <run_id> [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--force` | Force cancellation without confirmation |

#### Example

```bash
launch cancel aspose-note-foss-python-main-20260128
```

---

### `launch mcp serve`

Start the Model Context Protocol (MCP) server for Claude Desktop integration.

```bash
launch_mcp [options]
```

#### Options

| Flag | Description |
|------|-------------|
| `--host` | Listen host (default: 127.0.0.1) |
| `--port` | Listen port (default: 8787) |

#### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "foss-launcher": {
      "command": "launch_mcp",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

---

## Exit Codes

Per [`specs/01_system_contract.md`](../specs/01_system_contract.md):

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Validation/config failure (recoverable) |
| `2` | Execution failure (runtime error) |
| `3` | External service failure (GitHub, telemetry) |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub API access (required for repo cloning, commit service) |
| `TELEMETRY_TOKEN` | Local telemetry API auth (optional) |
| `MCP_AUTH_TOKEN` | MCP server auth token (optional) |
| `TELEMETRY_API_URL` | Telemetry API endpoint (default: http://localhost:8765) |

---

## See Also

- [`docs/reference/config.md`](./config.md) - Run configuration reference
- [`specs/01_system_contract.md`](../specs/01_system_contract.md) - System contract & exit codes
- [`specs/19_toolchain_and_ci.md`](../specs/19_toolchain_and_ci.md) - Toolchain and CI
- [`specs/14_mcp_endpoints.md`](../specs/14_mcp_endpoints.md) - MCP endpoints
- [`specs/43_resumable_pipeline.md`](../specs/43_resumable_pipeline.md) - Resumable pipeline spec (TC-2398/TC-2399)
