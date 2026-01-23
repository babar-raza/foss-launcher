# CLI Usage and Runbooks

This document provides operational runbooks for the FOSS Launcher CLI entrypoints.

## Prerequisites

- Python >= 3.12
- Repository installed (see [README.md](../README.md))
- Virtual environment `.venv` activated (mandatory, see [specs/00_environment_policy.md](../specs/00_environment_policy.md))

## CLI Entrypoints

The FOSS Launcher provides three console scripts, installed via `pyproject.toml`:

1. **`launch_run`** - Main orchestration runner
2. **`launch_validate`** - Validation and gate runner
3. **`launch_mcp`** - MCP server for Claude Desktop integration

### Installation

After cloning the repository:

```bash
# Preferred: deterministic install with uv
uv sync

# Fallback: pip install (non-deterministic)
python -m pip install -e ".[dev]"
```

### Verification

Check that console scripts are installed:

```bash
launch_run --help
launch_validate --help
launch_mcp --help
```

If console scripts are not in PATH, you can invoke directly:

```bash
python -c "from launch.cli import main; main()" --help
python -c "from launch.validators.cli import main; main()" --help
python -c "from launch.mcp.server import main; main()" --help
```

## Runbook: launch_run

**Purpose**: Execute the full FOSS Launcher orchestration pipeline.

### Basic Usage

```bash
launch_run --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
```

### Common Flags

- `--config PATH` - Path to run_config YAML (required)
- `--dry-run` - Validate config without executing (if implemented)
- `--verbose` - Increase logging verbosity (if implemented)

### Expected Outputs

- **RUN_DIR**: Created at `runs/<run_id>/`
- **Logs**: Console output + structured logs in RUN_DIR
- **Exit Codes**:
  - `0` - Success
  - `1` - Validation failure
  - `2` - Execution failure
  - See [specs/01_system_contract.md](../specs/01_system_contract.md) for full mapping

### Common Failures

#### Config Validation Failure

**Symptom**: Exit code 1, error "Invalid run_config schema"

**Fix**:
1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('path/to/config.yaml'))"`
2. Check schema compliance: `launch_validate --config path/to/config.yaml`
3. Review specs/schemas/run_config.schema.json for required fields

#### Missing Environment Variables

**Symptom**: Exit code 1, error "Required environment variable not set"

**Fix**:
1. Review specs/schemas/run_config.schema.json for required env vars
2. Set missing variables:
   - `GITHUB_TOKEN` - GitHub API access
   - `TELEMETRY_TOKEN` - Local telemetry API auth (optional)
3. Retry command

#### GitHub API Rate Limit

**Symptom**: Exit code 2, error "GitHub API rate limit exceeded"

**Fix**:
1. Wait for rate limit reset (check headers in logs)
2. Use authenticated token with higher limits
3. Reduce parallel operations if applicable

## Runbook: launch_validate

**Purpose**: Run validation gates without executing orchestration.

### Basic Usage

```bash
# Validate a run directory
launch_validate --run_dir runs/<run_id> --profile ci

# Validate a config file
launch_validate --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
```

### Validation Profiles

- `dev` - Minimal gates for local development
- `ci` - Full gates for CI/PR checks
- `release` - Strictest gates for production releases

### Expected Outputs

- **Console**: Gate-by-gate pass/fail report
- **Exit Codes**:
  - `0` - All gates pass
  - `1` - One or more gates fail

### Common Failures

#### Gate Failure: Schema Validation

**Symptom**: "Config schema validation failed"

**Fix**:
1. Review JSON-Schema error messages in output
2. Fix config file per specs/schemas/run_config.schema.json
3. Re-run validation

#### Gate Failure: Toolchain Lock

**Symptom**: "Toolchain versions don't match lock file"

**Fix**:
1. Check `uv.lock` is committed and up-to-date
2. Run `uv sync --frozen` to ensure locked versions
3. Re-run validation

## Runbook: launch_mcp

**Purpose**: Start the Model Context Protocol (MCP) server for Claude Desktop integration.

### Basic Usage

```bash
launch_mcp --host 127.0.0.1 --port 8000
```

### MCP Server Configuration

Add to Claude Desktop config (`claude_desktop_config.json`):

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

### Available Tools

See [specs/14_mcp_endpoints.md](../specs/14_mcp_endpoints.md) for full tool catalog.

Key tools:
- `launch_start_run_from_product_url` - Start run from Aspose product URL
- `launch_start_run_from_github_repo_url` - Start run from GitHub repo URL

### Common Failures

#### Server Won't Start

**Symptom**: "Address already in use"

**Fix**:
1. Check if port is in use: `netstat -an | grep 8000` (Linux/macOS) or `netstat -an | findstr 8000` (Windows)
2. Kill existing process or use different port: `launch_mcp --port 8001`

#### Claude Desktop Can't Connect

**Symptom**: MCP server running but Claude Desktop shows connection error

**Fix**:
1. Check Claude Desktop logs for error details
2. Verify `claude_desktop_config.json` syntax
3. Ensure `launch_mcp` is in PATH or use full path
4. Restart Claude Desktop

## Escalation

For issues not covered here:

1. Check [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) for known gaps
2. Review [specs/README.md](../specs/README.md) for binding specifications
3. File an issue in the repository with:
   - Exact command run
   - Full error output
   - Environment details (OS, Python version, uv version)

## Exit Code Reference

Per [specs/01_system_contract.md](../specs/01_system_contract.md):

- `0` - Success
- `1` - Validation/config failure (recoverable)
- `2` - Execution failure (runtime error)
- `3` - External service failure (GitHub, telemetry)

## See Also

- [README.md](../README.md) - Installation and quick start
- [specs/19_toolchain_and_ci.md](../specs/19_toolchain_and_ci.md) - CI integration
- [plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md](../plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md) - Implementation taskcard
