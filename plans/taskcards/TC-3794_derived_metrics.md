---
id: TC-3794
title: "Derived Metrics Calculator"
status: Done
priority: Normal
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, metrics, observability]
depends_on: [TC-3792]
allowed_paths:
  - plans/taskcards/TC-3794_derived_metrics.md
  - src/launcher/shared/metrics_calculator.py
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/shared/test_metrics_calculator.py
evidence_required:
  - reports/agents/telemetry/TC-3794/evidence.md
---

# Taskcard TC-3794 — Derived Metrics Calculator

## Objective

Implement pipeline-level metrics derivation from events.ndjson per the telemetry spec, calculating total_duration_s, worker_durations, llm_call_count, llm_total_tokens, fallback_count, cache_hit_rate, gate_pass_rate, and re_run_count.

## Required spec references

- `specs/toolchain_ci_telemetry.md` (Section: Pipeline-Level Metrics — all 8 metrics defined)

## Scope

### In scope
- Create `src/launcher/shared/metrics_calculator.py` with `calculate_pipeline_metrics()`
- Read events.ndjson and derive all 8 metrics from the spec
- Integrate cache stats from `get_cache_stats()` for cache_hit_rate
- Call from run_loop.py after graph execution completes
- Write result to `{run_dir}/pipeline_metrics.json`

### Out of scope
- Quality metrics (already handled by Evaluate worker in quality_metrics.json)
- Telemetry API server (TC-3796)
- Modifying event schema

## Inputs

- `{run_dir}/events.ndjson` — event stream
- Cache stats from `shared/cache_telemetry.get_cache_stats()`

## Outputs

- `{run_dir}/pipeline_metrics.json` — derived metrics
- `src/launcher/shared/metrics_calculator.py` — calculation module

## Allowed paths

- plans/taskcards/TC-3794_derived_metrics.md
- src/launcher/shared/metrics_calculator.py
- src/launcher/orchestrator/run_loop.py
- tests/unit/shared/test_metrics_calculator.py

### Allowed paths rationale
- metrics_calculator.py: new module for metric derivation
- run_loop.py: call metrics calculator after graph execution
- test file: verification

## Implementation steps

### Step 1: Create metrics_calculator.py

```python
def calculate_pipeline_metrics(events_path: Path) -> dict[str, Any]:
    """Derive pipeline metrics from events.ndjson."""
```

Parse events and calculate:
1. `total_duration_s`: time from first run_created to last worker_completed
2. `worker_durations`: dict of {worker_name: duration_ms} from worker_started/completed pairs
3. `llm_call_count`: count of llm_call_completed events
4. `llm_total_tokens`: sum of token_usage.total_tokens from llm_call_completed
5. `fallback_count`: count of llm_call_completed where endpoint contains "fallback" (or from cache stats)
6. `cache_hit_rate`: from get_cache_stats() — hit / (hit + miss) or 0.0
7. `gate_pass_rate`: count of gate_executed where passed=true / total gate_executed
8. `re_run_count`: count of re_run_triggered events

### Step 2: Integrate into run_loop.py

After graph execution (before returning RunResult), call:
```python
from launcher.shared.metrics_calculator import calculate_pipeline_metrics
metrics = calculate_pipeline_metrics(layout.events_file)
store.write_json("pipeline_metrics.json", metrics)
```

### Step 3: Write unit tests

- Test with fixture events.ndjson containing known events
- Test empty events file returns zeroed metrics
- Test each metric calculation individually

## Failure modes

### Failure mode 1: events.ndjson missing or corrupt
**Detection**: FileNotFoundError or JSON parse error
**Resolution**: Return zeroed metrics dict (non-fatal)
**Gate**: Test with missing/corrupt file

### Failure mode 2: Event schema mismatch
**Detection**: KeyError when accessing event fields
**Resolution**: Use .get() with defaults for all field access
**Gate**: Test with minimal events

### Failure mode 3: Division by zero in rates
**Detection**: ZeroDivisionError in cache_hit_rate or gate_pass_rate
**Resolution**: Return 0.0 when denominator is 0
**Gate**: Test with zero counts

## Task-specific review checklist

1. [ ] All 8 metrics from spec calculated
2. [ ] Non-fatal (never crashes pipeline)
3. [ ] Division-by-zero handled
4. [ ] Events parsed with .get() defaults
5. [ ] Cache stats integrated from cache_telemetry
6. [ ] Output written to pipeline_metrics.json

## Deliverables

1. `src/launcher/shared/metrics_calculator.py`
2. Modified `src/launcher/orchestrator/run_loop.py`
3. `tests/unit/shared/test_metrics_calculator.py`

## Acceptance checks

1. [ ] All 8 metrics calculated correctly
2. [ ] Handles empty/missing events gracefully
3. [ ] All existing tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] All 8 metrics verified
- [ ] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_metrics_calculator.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- Metrics calculator tests pass
- No regressions

## Integration boundary proven

**Upstream**: events.ndjson from event_log; cache stats from cache_telemetry (TC-3791)
**Downstream**: pipeline_metrics.json consumed by CI/reporting
**Contract**: `calculate_pipeline_metrics(events_path: Path) -> dict[str, Any]` with 8 known keys
