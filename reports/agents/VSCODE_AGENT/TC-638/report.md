# TC-638 Report: Fix W4 IAPlanner Type Error

**Agent**: VSCODE_AGENT
**Taskcard**: TC-638
**Date**: 2026-01-30
**Status**: COMPLETE

## Summary

Fixed the W4 IAPlanner `'list' object has no attribute 'get'` error that blocked Pilot-1 E2E completion.

## Problem

In `determine_launch_tier()`, line 196 assumed `example_inventory` is a dict:
```python
example_roots = product_facts.get("example_inventory", {}).get("example_roots", [])
```

But W2 FactsBuilder produces `example_inventory` as a **LIST** of example objects in actual runs.

## Solution

Made `determine_launch_tier()` handle both formats:
```python
example_inventory = product_facts.get("example_inventory", [])
if isinstance(example_inventory, list):
    example_roots = example_inventory
elif isinstance(example_inventory, dict):
    example_roots = example_inventory.get("example_roots", [])
else:
    example_roots = []
```

## Commands Run

```bash
# Baseline verification
.venv\Scripts\python.exe tools\validate_swarm_ready.py
.venv\Scripts\python.exe -m pytest -q

# Unit tests (before fix - 3 failed)
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_638_w4_ia_planner.py -v

# Unit tests (after fix - 5 passed)
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_638_w4_ia_planner.py -v

# Pilot E2E
OFFLINE_MODE=1 LAUNCH_GIT_SHALLOW=1 .venv\Scripts\python.exe scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python
```

## Evidence

### Run Directories
- Run 1: runs/r_20260129T200943Z_3d-python_5c8d85a_f04c8553/
- Run 2: runs/r_20260129T201052Z_3d-python_5c8d85a_f04c8553/

### Artifact Paths
- page_plan.json: runs/r_20260129T201052Z_3d-python_5c8d85a_f04c8553/artifacts/page_plan.json

### Checksums
- page_plan.json SHA256: d9e07042fe02c9a0d9f8f0b24bcc13791745e54de33bd983b5a22b4c855cf978

### Determinism
- Run 1 and Run 2 produce identical page_plan.json (PASS)

## Acceptance Criteria Checklist

| ID | Criterion | Status |
|----|-----------|--------|
| A | W4 no longer throws type error | PASS |
| B | Unit test reproduces old failure and passes after fix | PASS (5/5) |
| C | Pilot-1 E2E proceeds beyond W4 | PASS (page_plan.json produced) |
| D | validate_swarm_ready 21/21 PASS | PASS |
| E | pytest PASS | PASS |

## Files Changed
- src/launch/workers/w4_ia_planner/worker.py (fix)
- tests/unit/workers/test_tc_638_w4_ia_planner.py (new test file)
- plans/taskcards/TC-638_fix_w4_ia_planner_type_error.md (new taskcard)
- plans/taskcards/INDEX.md (updated)
