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

## Overview

The `launch` CLI provides commands for:

- Starting documentation generation runs
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
