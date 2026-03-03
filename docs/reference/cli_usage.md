# CLI Usage and Runbooks

This document provides operational runbooks for the FOSS Launcher CLI entrypoints.

## Prerequisites

- Python >= 3.12
- Repository installed (see [README.md](../../README.md))
- Virtual environment `.venv` activated (mandatory, see [specs/00_environment_policy.md](../../specs/00_environment_policy.md))

## CLI Entrypoints

The FOSS Launcher provides three console scripts, installed via `pyproject.toml`:

1. **`launch_run`** - Main orchestration runner (full pipeline, W1→W11)
2. **`launch resume`** - Resume from any worker (incremental debugging)
3. **`launch_validate`** - Validation and gate runner
4. **`launch_mcp`** - MCP server for Claude Desktop integration

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
  - See [specs/01_system_contract.md](../../specs/01_system_contract.md) for full mapping

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

## Runbook: launch resume (Incremental Debugging)

**Purpose**: Re-enter the pipeline at any worker without re-running the full 60–90 min pipeline
from W1. Designed for the debugging loop: run → fail at W5 → fix W5 code → resume from W5.

**Spec**: [`specs/43_resumable_pipeline.md`](../../specs/43_resumable_pipeline.md)

### Prerequisites

A completed or partially completed run must exist in `runs/`. The run directory must contain
artifacts produced by all workers *before* the `--from-worker` entry point.

### Basic Usage

```bash
# Resume from W5 (SectionWriter) — skips W1–W4 entirely
.venv/Scripts/python.exe -m launch resume \
    --run-dir runs/r_20260221T123456Z_launch_pilot-aspose-3d-foss-python_XXXX \
    --from-worker W5

# Via pilot script — auto-discovers the most recent run for that pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
    --pilot pilot-aspose-3d-foss-python \
    --from-worker W5
```

### Typical Debugging Workflow

```bash
# 1. Run the full pipeline (first time or after a major change)
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
    --pilot pilot-aspose-3d-foss-python

# 2. Pipeline fails or produces bad output in W5. Fix your code.

# 3. Resume from W5 — W1–W4 artifacts are reused
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
    --pilot pilot-aspose-3d-foss-python --from-worker W5

# 4. If the fix is good, re-run the full pipeline for a clean final artifact set.
```

### Finding a Run Directory

```bash
# List recent runs (newest first by default)
.venv/Scripts/python.exe -m launch list --limit 10

# Or inspect the manifest directly
python -c "
import json
for line in open('runs/manifest.jsonl'):
    r = json.loads(line)
    print(r.get('run_id'), r.get('pilot_id'), r.get('state', {}).get('run_state'))
" | tail -5
```

### Common Flags

| Flag | Description |
|------|-------------|
| `--run-dir PATH` | Existing run directory (required) |
| `--from-worker ALIAS` | `W1`–`W11` or full node name like `draft_sections` (required) |
| `--verbose` | Verbose logging |

### Expected Outputs

- **Events**: `RUN_RESUMED` event appended to `runs/<run_id>/events.ndjson`
- **Artifacts**: Artifacts from `--from-worker` onward are overwritten; earlier artifacts kept
- **Exit Codes**:
  - `0` — Run completed (examine run state for content pass/fail)
  - `1` — Validation failure (unknown alias, missing artifacts, missing `run_config.yaml`)
  - `2` — Execution error during graph streaming

### Verifying the Resume Event

```bash
# Confirm RUN_RESUMED was appended to events log
python -c "
import json
for line in open('runs/r_20260221T.../events.ndjson'):
    e = json.loads(line)
    if e.get('type') == 'RUN_RESUMED':
        print(e)
"
```

### Common Failures

#### Unknown Worker Alias

**Symptom**: Exit code 1, "Unknown worker alias 'WXYZ'. Valid aliases: W1, W2, ..."

**Fix**: Use `W1`–`W11` (short) or a full node name (`clone_inputs`, `draft_sections`, etc.).
Run `launch resume --help` to see option description.

#### Missing Required Artifacts

**Symptom**: Exit code 1, "Missing required artifacts: artifacts/page_plan.json, ..."

**Cause**: The run directory does not have artifacts from all prior workers.
This happens if you resume from a point *earlier* than where the previous run reached.

**Fix**:
1. Resume from a later worker that has all required artifacts, OR
2. Run the full pipeline first so all artifacts are produced.

#### `run_config.yaml` Not Found

**Symptom**: Exit code 1, "run_config.yaml not found in run_dir"

**Fix**: Ensure `--run-dir` points to a valid run directory that was created by `launch run`.
The file should be at `runs/<run_id>/run_config.yaml`.

#### run_dir Outside runs/ Root

**Symptom**: Exit code 1, "run_dir is not under the configured runs root"

**Fix**: Use the full path under `runs/`. Do not pass arbitrary directories.

---

## Runbook: launch drive (Autopilot Self-Driving)

**Purpose**: Auto-determine the earliest safe pipeline entry point and execute.
Eliminates manual `launch resume --from-worker` guesswork by inspecting artifacts
and a persistent state store.

**Spec**: [`specs/48_autopilot_phase_selection.md`](../../specs/48_autopilot_phase_selection.md)

**Architecture**: [`docs/architecture/autopilot.md`](../architecture/autopilot.md)

### Basic Usage

```bash
# First run (no cached artifacts → starts from W1)
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml

# With real-time event monitoring
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --live

# Goal: produce a PR (runs through W11)
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --goal pr

# Validate only (no fix loop, no PR)
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --goal validate

# Auto-heal: triage-driven fix loop when validation fails
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --heal

# Heal + PR: auto-heal, then open PR if all gates pass
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --goal pr --heal

# With LLM planner advisory
launch drive --config configs/pilots/pilot-aspose-cells-foss-python.yaml --llm
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--config PATH` | Path | (required) | Path to run_config YAML file |
| `--goal` | string | `draft` | Pipeline goal: `draft`, `validate`, or `pr` |
| `--heal` | flag | off | Auto-enter heal loop for fixable validation issues |
| `--llm` | flag | off | Enable LLM planner advisory |
| `--verbose` / `-v` | flag | off | Increase logging verbosity |
| `--live` | flag | off | Show real-time event progress |

### How It Works

1. Loads and validates the run config
2. Resolves the state store key (`family/platform`)
3. Searches the store for cached artifacts matching the target `github_ref` (SHA)
4. Creates a new run directory and hydrates it with cached artifacts (if found)
5. Runs the deterministic PhaseSelector to find the earliest safe start worker
6. Optionally consults the LLM planner (if `--llm`)
7. Writes `execution_plan.json` to `run_dir/artifacts/`
8. Executes the pipeline from the computed start worker (respects `--goal`)
9. If `--heal` and validation failed, enters triage-driven heal loop
10. If heal converges and `--goal=pr`, executes W11
11. On success, publishes W1-W4 artifacts to the store for future reuse

### Goal Behavior

**`--goal=validate`** (one-shot validation):
```
Pipeline: W1 → ... → W9 → stop
No fix loop, no PR. Exit 0 if all gates pass, exit 1 otherwise.
```

**`--goal=draft`** (default):
```
Pipeline: W1 → ... → W9 → [fix loop] → stop
Fix loop runs if fixable issues exist. Never calls W11 (no PR).
Exit 0 if validation passes, exit 1 otherwise.
```

**`--goal=pr`**:
```
Pipeline: W1 → ... → W9 → [fix loop] → W11
Full pipeline including PR. Exit 0 on success, exit 2 on failure.
```

### Heal Behavior

When `--heal` is set, the drive command enters a triage-driven heal loop after
the initial pipeline run if validation has failures:

```
Pipeline execution → validation fails → triage → resume from recommended worker
→ re-validate → repeat (up to 5 steps)
```

If heal converges (all gates pass) and `--goal=pr`, W11 is automatically executed.

### Typical Flows

**First run (no store)**:
```
State store: empty
PhaseSelector: W1 (no artifacts)
Pipeline: W1 → W2 → ... → W9
Store publish: W1-W4 artifacts cached
```

**Second run (same SHA)**:
```
State store: has W1-W4 for this SHA
Hydration: 12 artifacts copied
PhaseSelector: W5 (W1-W4 ready, no drafts)
Pipeline: W5 → W6 → ... → W9
Store publish: no new W1-W4 to publish
```

**SHA changed**:
```
State store: has W1-W4 for OLD sha
Hydration: no match for new SHA
PhaseSelector: W1 (repo_sha mismatch)
Pipeline: W1 → W2 → ... → W9
Store publish: W1-W4 for new SHA cached
```

### Exit Codes

- `0` — Success (all validation gates pass)
- `1` — Validation failure (gates did not pass) or argument error
- `2` — Execution failure (pipeline crash)

### Configuration

Add the optional `autopilot` block to your run_config YAML:

```yaml
autopilot:
  enabled: true
  state_store_root: ".foss_state"      # default: .foss_state/
  llm_planner_enabled: false           # default: false
```

### Troubleshooting

#### "WARNING: RUN_DIR already exists"

The run ID collided with an existing run. Use `launch resume` to continue
an existing run, or delete the old run directory.

#### "WARNING: Hydration failed"

The state store exists but file copy failed (permissions, disk full, etc.).
The drive command falls back to W1 automatically. Check disk space and
file permissions on the store root.

#### "StoreConflictError" on publish

Two different runs produced different content for the same artifact + SHA.
Check `<store_root>/<key>/conflicts/<sha>/` for the conflicting files.
This typically indicates a determinism bug in a worker.

---

## Runbook: launch triage (Post-Validation Diagnosis)

**Purpose**: Diagnose a validation report and recommend the fastest path to a green run.
Reads `validation_report.json` from a completed W9 pass and prints three sections:
a summary, the top issues ranked by severity, and recommended `launch resume` commands.

**TC-2900**

### Basic Usage

```bash
# Triage by run_id (looks up runs/<run_id>/)
launch triage r_20260226T120000Z_launch_pilot-aspose-3d-foss-python_1234

# Triage by explicit run directory
launch triage dummy --run-dir runs/r_20260226T120000Z_.../

# Show top 20 issues instead of default 10
launch triage r_20260226T... --top 20
```

### Sample Output

```
== Triage Summary ==

  Run ID:        r_20260226T120000Z_...
  Run state:     DONE
  Profile:       local
  Gates:         41 total, 3 failed
  Issues:        0 blocker, 5 error, 12 warn, 8 info

== Top Issues ==

  Sev      Gate                          Code           Path                    Line  Message
  error    gate_15b_code_fence_api       CF-API-001     work/site/.../faq.md      42  Unknown symbol: aspose.threed.Foo
  error    gate_scaffold_leak            SCAFFOLD_LEAK  work/site/.../guide.md    10  Pipeline diagnostic in content
  ...

== Recommended Next Step ==

  1. Hallucinated API symbols in code fences
     launch resume --run-dir runs/r_... --from-worker W5

  2. Scaffold/prompt leak or formatting issues (W10 auto-fixable)
     launch resume --run-dir runs/r_... --from-worker W10
```

### Recommendation Mapping

| Condition | Recommended Worker | Rationale |
|---|---|---|
| Gate 0 (`gate_truth_layer_completeness`) or Gate 40 failed | **W2** | Truth artifacts missing/incomplete |
| Gate 15b (`gate_15b_code_fence_api`) failed | **W5** | Hallucinated API symbols need re-drafting |
| `gate_scaffold_leak` failed or `FQ-*`/`G17-*` error codes | **W10** | Scaffold/formatting auto-fixable by W10 |
| Link or patch gates failed (gates 5, 12) | **W8** | Cross-page linking pass |
| No specific pattern | **W9** | General re-validation |

### Exit Codes

- `0` — Triage printed successfully
- `1` — Validation report not found (run `launch validate` first)

---

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

- `local` - Minimal gates for local development (fast feedback, skip external links)
- `ci` - Full gates for CI/PR checks (comprehensive validation)
- `prod` - Strictest gates for production releases (maximum rigor, zero tolerance for warnings)

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

See [specs/14_mcp_endpoints.md](../../specs/14_mcp_endpoints.md) for full tool catalog.

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

## Runbook: Preflight Validation

**Purpose:** Verify the repository is swarm-ready before starting agent work.

### Basic Usage

```bash
# From activated .venv:
python tools/validate_swarm_ready.py

# Or without activation (use .venv/bin/python explicitly):
# Windows:
.venv\Scripts\python tools\validate_swarm_ready.py
# Linux/macOS:
.venv/bin/python tools/validate_swarm_ready.py
```

### What It Checks

See [specs/09_validation_gates.md](../../specs/09_validation_gates.md) for the full gate catalog.

Key gates:
- **Gate 0:** Environment policy (.venv compliance)
- **Gate A:** Spec pack integrity (schemas valid)
- **Gate B:** Taskcard frontmatter validity
- **Gate D:** Markdown link health (0 broken links)
- **Gate K:** Supply chain pinning (uv.lock enforced)

### Expected Output

```
Running preflight validation...
[Gate 0] Environment policy: PASS
[Gate A] Spec pack integrity: PASS
[Gate B] Taskcard frontmatter: PASS
[Gate D] Markdown links: PASS
[Gate K] Supply chain pinning: PASS
...
All gates PASS. Repository is swarm-ready.
```

**Exit code:** 0 (success)

### Common Failures

#### Gate 0 Failure: Not in .venv

**Symptom:**
```
FAIL: Not running from .venv
Expected: sys.prefix ends with '.venv'
Actual: /usr/bin/python (or C:\Python312)
```

**Fix:**
1. Activate `.venv`:
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/macOS
   source .venv/bin/activate
   ```
2. Re-run validation: `python tools/validate_swarm_ready.py`

#### Gate K Failure: Supply chain pinning

**Symptom:**
```
FAIL: uv.lock not being used
Cannot verify deterministic dependency installation
```

**Fix:**
1. Ensure you're in `.venv` (see Gate 0 fix above)
2. Run `uv sync --frozen` to install from lockfile
3. Re-run validation

#### Gate D Failure: Broken links

**Symptom:**
```
FAIL: 34 broken link(s) found
See: reports/link_check.txt
```

**Fix:**
1. Review broken links report
2. Fix links in markdown files
3. Re-run link checker: `python tools/check_markdown_links.py`
4. Re-run preflight validation

### Troubleshooting

For detailed setup and troubleshooting, see:
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Environment setup guide
- [specs/00_environment_policy.md](../../specs/00_environment_policy.md) - .venv policy spec
- [specs/09_validation_gates.md](../../specs/09_validation_gates.md) - Full gate specifications

## Escalation

For issues not covered here:

1. Check [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) for known gaps
2. Review [specs/README.md](../../specs/README.md) for binding specifications
3. File an issue in the repository with:
   - Exact command run
   - Full error output
   - Environment details (OS, Python version, uv version)

## Exit Code Reference

Per [specs/01_system_contract.md](../../specs/01_system_contract.md):

- `0` - Success
- `1` - Validation/config failure (recoverable)
- `2` - Execution failure (runtime error)
- `3` - External service failure (GitHub, telemetry)

## See Also

- [README.md](../../README.md) - Installation and quick start
- [specs/19_toolchain_and_ci.md](../../specs/19_toolchain_and_ci.md) - CI integration
- [specs/43_resumable_pipeline.md](../../specs/43_resumable_pipeline.md) - Resumable pipeline spec (TC-2398/TC-2399)
- [docs/reference/cli.md](./cli.md) - Full CLI reference (options, exit codes, aliases)
- [plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md](../../plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md) - Implementation taskcard
