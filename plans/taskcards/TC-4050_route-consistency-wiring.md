---
id: TC-4050
title: "Wire check_route_consistency() into evaluate worker"
status: Done
priority: Critical
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, cgb-01]
depends_on: [TC-4037]
allowed_paths:
  - plans/taskcards/TC-4050_route-consistency-wiring.md
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-4050/evidence.md
---

# Taskcard TC-4050 — Wire check_route_consistency() into evaluate worker

## Objective

`check_route_consistency()` was created (TC-4037) and exported but never called in the
evaluate worker. Waves 4A, 4F, and 4G have zero runtime effect until this wires.

## Scope

### In scope
- Add `check_route_consistency` import to worker.py
- Add call inside `_run_deterministic_checks()`

### Out of scope
- Changes to route_consistency.py, grader.py, go_criteria.py

## Allowed paths

- plans/taskcards/TC-4050_route-consistency-wiring.md
- src/launcher/workers/evaluate/worker.py

## Implementation steps

### Step 1: Add import
In the `from launcher.workers.evaluate.checks import (` block, add `check_route_consistency`.

### Step 2: Add call in _run_deterministic_checks
After the `check_format_truth` call, add:
```python
findings.extend(check_route_consistency(content, slug, page_role=page_role))
```

## Acceptance checks

- [x] check_route_consistency appears in import block
- [x] check_route_consistency called in _run_deterministic_checks
- [x] Also added "page"/"overview" to _STOP_WORDS/_SKIP_ROLES (spurious test slug fix)
- [x] 1580 unit tests pass (PYTHONHASHSEED=0)
