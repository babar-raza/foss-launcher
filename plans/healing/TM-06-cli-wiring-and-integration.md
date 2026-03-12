---
id: TM-06
title: "Telemetry API: Wire CLI command and document data flow"
status: Not Started
priority: Medium
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, integration, cli]
depends_on: [TM-04]
allowed_paths:
  - plans/healing/TM-06-cli-wiring-and-integration.md
  - src/launcher/cli/main.py
  - tests/unit/telemetry_api/test_server.py
evidence_required:
  - reports/healing/TM-06/evidence.md
---

# Taskcard TM-06 — Wire CLI Command and Document Data Flow

## Status: Not Started

## Gap linkage
- **G-TM-15**: No CLI command to start the telemetry server. v1 had `launch telemetry-server`; v2's `src/launcher/cli/main.py` has no equivalent. Users cannot start the server without writing Python code.
- **G-TM-16**: No documentation of TelemetryClient -> API Server -> SQLite data flow. The wiring between `run_loop.py` (env var `TELEMETRY_API_URL`) and this server is implicit.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
1. Add `telemetry-server` command to `src/launcher/cli/main.py` (Typer app) that calls `start_telemetry_server()` with CLI options for `--host`, `--port`, `--db-path`, `--log-level`
2. Guard the import with try/except for when fastapi is not installed (print helpful error message)
3. Add a test that the CLI command is registered and shows in `--help` (when fastapi is available)

### Allowed paths:
- `plans/healing/TM-06-cli-wiring-and-integration.md`
- `src/launcher/cli/main.py`
- `tests/unit/telemetry_api/test_server.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `launch telemetry-server --help` shows options for host, port, db-path, log-level
- `launch telemetry-server` starts server on 127.0.0.1:8765 (when fastapi installed)
- `launch telemetry-server` without fastapi prints "Install with: pip install foss-launcher[telemetry-api]"

### UI/Web/API:
- Started server responds to `GET /health`

### Tests:
- Test that `telemetry-server` appears in CLI help output
- All existing tests still pass

### Config respected end-to-end:
- CLI options override env vars override defaults
- `--db-path` controls where SQLite file is created

### No mock data in production paths:
- N/A

## Deliverables
- Modified `src/launcher/cli/main.py` with `telemetry-server` command
- Updated `tests/unit/telemetry_api/test_server.py` with CLI registration test
- Full file replacements (no stubs, no TODOs)

## Hard rules
- Keep public CLI signatures for existing commands unchanged
- Keep entrypoints in parity: CLI command mirrors `start_telemetry_server()` API
- No network in offline tests (don't actually start the server in test)
- No new deps (Typer already a dependency; fastapi guarded by try/except)
- Deterministic — PYTHONHASHSEED=0

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | CLI command exposes all server config options |
| Consistency | CLI style matches existing commands in main.py |
| Production grading | Graceful degradation without fastapi; helpful error message |
| Systematic approach | Read main.py first, add command following existing patterns |
| Correctness & spec alignment | CLI options match ServerConfig fields |
| Scope & constraints | Only 2 files touched |
| Maintainability | Command is thin wrapper around start_telemetry_server() |
| Testability | CLI help test doesn't require running the server |
| Robustness | Missing fastapi → clear error, not ImportError traceback |
| Performance | N/A |
| Integration | CLI → start_telemetry_server → create_app → uvicorn |
| Observability | Server startup logged at INFO level |
| Minimality | ~20 lines added to main.py |

## Now (runbook)

```bash
# 1. Read current CLI structure
cat src/launcher/cli/main.py | head -50

# 2. Add telemetry-server command following existing pattern
# 3. Add try/except guard for fastapi import

# 4. Test CLI help
.venv/Scripts/python.exe -m launcher.cli.main telemetry-server --help

# 5. Add test
# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v

# 7. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
