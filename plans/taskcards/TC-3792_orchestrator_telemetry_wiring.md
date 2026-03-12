---
id: TC-3792
title: "Orchestrator Telemetry Wiring"
status: Done
priority: High
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, orchestrator, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3792_orchestrator_telemetry_wiring.md
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/models/run_config.py
  - tests/unit/orchestrator/test_telemetry_wiring.py
evidence_required:
  - reports/agents/telemetry/TC-3792/evidence.md
---

# Taskcard TC-3792 — Orchestrator Telemetry Wiring

## Objective

Wire the existing TelemetryClient into the orchestrator lifecycle so that pipeline runs create telemetry records, and thread the client through WorkerContext to make it available to workers.

## Required spec references

- `specs/toolchain_ci_telemetry.md` (Section: Telemetry Events — pipeline-level metrics)
- `specs/11_state_and_events.md` (Section: State transitions and events)

## Scope

### In scope
- Add optional `telemetry_client` field to WorkerContext
- Add optional `telemetry_trace_id` field to WorkerContext
- Instantiate TelemetryClient in `execute_run()` when telemetry config is available
- Create parent telemetry run at pipeline start
- Update parent run on success/failure
- Flush outbox at end of run
- Add TelemetryConfig to RunConfig (optional, extra="ignore" already handles this)

### Out of scope
- Worker-level telemetry passthrough (TC-3793)
- Derived metrics (TC-3794)
- Gate execution tracking (TC-3795)
- Telemetry API server (TC-3796)

## Inputs

- `src/launcher/clients/telemetry.py` — TelemetryClient (already implemented)
- `src/launcher/orchestrator/run_loop.py` — execute_run entry point
- `src/launcher/orchestrator/worker_contract.py` — WorkerContext class

## Outputs

- Modified `WorkerContext` with telemetry_client and telemetry_trace_id properties
- Modified `execute_run()` with telemetry lifecycle
- Unit tests

## Allowed paths

- plans/taskcards/TC-3792_orchestrator_telemetry_wiring.md
- src/launcher/orchestrator/worker_contract.py
- src/launcher/orchestrator/run_loop.py
- src/launcher/models/run_config.py
- tests/unit/orchestrator/test_telemetry_wiring.py

### Allowed paths rationale
- worker_contract.py: add telemetry_client to WorkerContext
- run_loop.py: instantiate TelemetryClient and manage lifecycle
- run_config.py: add TelemetryConfig model for endpoint config
- test file: verification

## Implementation steps

### Step 1: Add TelemetryConfig to run_config.py

Add an optional TelemetryConfig model:
```python
class TelemetryConfig(LauncherBaseModel):
    endpoint_url: str = "http://127.0.0.1:8765"
    auth_token_env: str = ""
```
Add `telemetry: TelemetryConfig | None = None` to RunConfig.

### Step 2: Add telemetry fields to WorkerContext

Add to `__init__`:
- `telemetry_client: TelemetryClient | None = None` parameter
- `telemetry_trace_id: str = ""` parameter

Add read-only properties for both.

### Step 3: Wire TelemetryClient in execute_run()

In execute_run():
1. Check if config has telemetry settings (via env var TELEMETRY_API_URL or config)
2. If available, create TelemetryClient(endpoint_url, run_dir)
3. Generate trace_id via generate_trace_id()
4. Create parent telemetry run (job_type="launch", agent_name="launcher.orchestrator")
5. Pass telemetry_client and trace_id when creating WorkerContext
6. On success: update run with status="success", duration_ms
7. On failure: update run with status="failure", error_summary
8. Always: flush_outbox() in finally block

### Step 4: Write unit tests

- Test WorkerContext accepts telemetry_client=None (backward compat)
- Test WorkerContext accepts telemetry_client=mock
- Test TelemetryConfig model validation
- Test execute_run creates telemetry run when configured

## Failure modes

### Failure mode 1: Telemetry failure crashes pipeline
**Detection**: Pipeline fails with TelemetryError
**Resolution**: Wrap all telemetry calls in try/except, log warnings, never raise
**Gate**: Test with unreachable telemetry endpoint

### Failure mode 2: WorkerContext backward incompatibility
**Detection**: Existing tests fail because new params are required
**Resolution**: All new params are optional with defaults (None/"")
**Gate**: Existing test suite passes

### Failure mode 3: RunConfig rejects telemetry config
**Detection**: RunConfig validation fails on existing configs
**Resolution**: RunConfig has extra="ignore", new field is Optional with default None
**Gate**: Existing pilot configs still parse

## Task-specific review checklist

1. [ ] WorkerContext backward-compatible (all new params optional)
2. [ ] TelemetryClient failures never crash pipeline
3. [ ] Outbox flushed in finally block (always runs)
4. [ ] trace_id generated once and shared across workers
5. [ ] Parent run created with correct job_type="launch"
6. [ ] Duration calculated correctly (start to end)

## Deliverables

1. Modified `src/launcher/orchestrator/worker_contract.py`
2. Modified `src/launcher/orchestrator/run_loop.py`
3. Modified `src/launcher/models/run_config.py`
4. `tests/unit/orchestrator/test_telemetry_wiring.py`
5. `reports/agents/telemetry/TC-3792/evidence.md`

## Acceptance checks

1. [ ] WorkerContext.telemetry_client property works
2. [ ] WorkerContext.telemetry_trace_id property works
3. [ ] execute_run works with telemetry=None (backward compat)
4. [ ] execute_run creates telemetry run when configured
5. [ ] All existing tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Backward compat verified
- [ ] Evidence captured: reports/agents/telemetry/TC-3792/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_telemetry_wiring.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- Telemetry wiring tests pass
- No regressions

## Integration boundary proven

**Upstream**: RunConfig provides TelemetryConfig; TelemetryClient already implemented
**Downstream**: WorkerContext.telemetry_client available to workers (TC-3793); trace_id shared
**Contract**: WorkerContext.telemetry_client: Optional[TelemetryClient]; WorkerContext.telemetry_trace_id: str
