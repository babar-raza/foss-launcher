---
id: TC-3795
title: "Gate Execution Tracking"
status: Done
priority: Normal
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, gates, observability]
depends_on: [TC-3792]
allowed_paths:
  - plans/taskcards/TC-3795_gate_execution_tracking.md
  - src/launcher/validation_engine/runner.py
  - tests/unit/validation_engine/test_gate_telemetry.py
evidence_required:
  - reports/agents/telemetry/TC-3795/evidence.md
---

# Taskcard TC-3795 — Gate Execution Tracking

## Objective

Emit `gate_executed` events from the validation engine runner after each gate executes, enabling gate_pass_rate metric calculation and gate-level observability.

## Required spec references

- `specs/toolchain_ci_telemetry.md` (Section: Pipeline-Level Metrics — gate_pass_rate)
- `specs/schemas/event_schemas/gate_executed.schema.json` (Event schema)

## Scope

### In scope
- Emit gate_executed event after each gate runs in runner.py
- Include gate_id, passed (bool), duration_ms, profile, and issue count
- Use ArtifactStore.emit_event for consistency with rest of pipeline

### Out of scope
- Modifying gate logic (adapters, gate_types)
- Adding new gate types
- Telemetry API server (TC-3796)

## Inputs

- `src/launcher/validation_engine/runner.py` — run_gates function
- `src/launcher/models/event.py` — EventType.gate_executed already defined

## Outputs

- Modified `runner.py` with gate_executed event emission
- Unit test

## Allowed paths

- plans/taskcards/TC-3795_gate_execution_tracking.md
- src/launcher/validation_engine/runner.py
- tests/unit/validation_engine/test_gate_telemetry.py

### Allowed paths rationale
- runner.py: add event emission after gate execution
- test file: verification

## Implementation steps

### Step 1: Add event emission to run_gates

After each gate executes (line 67: `gate_results.append`), emit a gate_executed event:

```python
# Emit gate_executed event (non-fatal)
try:
    from ..io.artifact_store import ArtifactStore
    store = ArtifactStore(run_dir=run_dir)
    store.emit_event("gate_executed", {
        "gate_id": gate_def.gate_id,
        "passed": ok,
        "profile": profile,
        "issue_count": len(issues),
    }, run_id=run_config.get("run_id", ""))
except Exception:
    pass  # telemetry is non-fatal
```

### Step 2: Handle skipped and error cases

Also emit for skipped gates and error cases with appropriate data.

### Step 3: Write unit test

Test that gate_executed events appear in events.ndjson after run_gates.

## Failure modes

### Failure mode 1: ArtifactStore construction fails
**Detection**: Exception when creating ArtifactStore in gate loop
**Resolution**: Wrap in try/except, pass (non-fatal)
**Gate**: Test with invalid run_dir

### Failure mode 2: Missing run_id in run_config
**Detection**: KeyError when accessing run_config["run_id"]
**Resolution**: Use .get("run_id", "")
**Gate**: Test with empty config

### Failure mode 3: Event emission slows gate execution
**Detection**: Gate execution time increases
**Resolution**: Event emission is a simple file append — negligible overhead
**Gate**: Timing test

## Task-specific review checklist

1. [ ] gate_executed emitted after each gate
2. [ ] Event includes gate_id, passed, profile, issue_count
3. [ ] Non-fatal (wrapped in try/except)
4. [ ] Skipped gates also emit events
5. [ ] Error gates emit with passed=False
6. [ ] No import cycles introduced

## Deliverables

1. Modified `src/launcher/validation_engine/runner.py`
2. `tests/unit/validation_engine/test_gate_telemetry.py`

## Acceptance checks

1. [ ] gate_executed events appear in events.ndjson
2. [ ] Events contain correct gate data
3. [ ] All existing tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Events verified in ndjson
- [ ] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/validation_engine/test_gate_telemetry.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- Gate telemetry tests pass
- No regressions

## Integration boundary proven

**Upstream**: Gate adapters provide ok/issues results
**Downstream**: gate_executed events consumed by metrics_calculator (TC-3794) for gate_pass_rate
**Contract**: Event type "gate_executed" with payload {gate_id: str, passed: bool, profile: str, issue_count: int}
