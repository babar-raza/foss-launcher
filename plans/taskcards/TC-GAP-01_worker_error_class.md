---
id: TC-GAP-01
title: "Introduce WorkerError and replace ValueError in checkpoint loaders"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [errors, evaluate, orchestrator, spec-compliance]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-GAP-01_worker_error_class.md
  - src/launcher/util/errors.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/orchestrator/run_loop.py
evidence_required:
  - reports/agents/TC-GAP-01/evidence.md
---

# Taskcard TC-GAP-01 — Introduce WorkerError and replace ValueError

## Objective

Add `WorkerError(LaunchError)` to the project error hierarchy and replace all
`ValueError` raises in checkpoint loader functions with it. This closes the
TC-HO-03 spec deviation where the plan specified `WorkerError` but no such class
existed at implementation time.

## Required spec references

- `specs/system_contract.md` (Section: Error handling contracts)
- `src/launcher/util/errors.py` (current error hierarchy)

## Scope

### In scope
- Define `WorkerError(LaunchError)` in `src/launcher/util/errors.py`
- Update `_load_understand_checkpoint` in `evaluate/worker.py` to raise `WorkerError`
- Update `_assert_understand_checkpoint` in `run_loop.py` to raise `WorkerError`
- Update any tests that assert `ValueError` from these functions

### Out of scope
- Replacing all `ValueError` raises elsewhere in the codebase (not in scope)
- Changing the orchestrator exception-handling strategy (catches `Exception` — OK)

## Inputs

- `src/launcher/util/errors.py` — current hierarchy
- `src/launcher/workers/evaluate/worker.py` — `_load_understand_checkpoint`
- `src/launcher/orchestrator/run_loop.py` — `_assert_understand_checkpoint`

## Outputs

- Updated `src/launcher/util/errors.py` with `WorkerError`
- Updated `evaluate/worker.py` raising `WorkerError`
- Updated `run_loop.py` raising `WorkerError`

## Allowed paths

- plans/taskcards/TC-GAP-01_worker_error_class.md
- src/launcher/util/errors.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/orchestrator/run_loop.py

### Allowed paths rationale

All three source files are protected paths requiring a taskcard. Taskcard file itself.

## Implementation steps

### Step 1: Add WorkerError to errors.py

Append after `FrontmatterError`:

```python
class WorkerError(LaunchError):
    """Raised when a worker cannot complete execution due to a missing dependency,
    malformed input, or invalid precondition (e.g. upstream checkpoint absent)."""
```

### Step 2: Update evaluate/worker.py

Add import: `from launcher.util.errors import WorkerError`

In `_load_understand_checkpoint`, replace both `raise ValueError(...)` with
`raise WorkerError(...)`. Update docstring `Raises` section to say `WorkerError`.

### Step 3: Update run_loop.py

Add import: `from launcher.util.errors import WorkerError`

In `_assert_understand_checkpoint`, replace `raise ValueError(...)` with
`raise WorkerError(...)`.

### Step 4: Scan and fix tests

Search tests for any assertion of `ValueError` from these two functions. Update
to assert `WorkerError` (or `LaunchError` as the base). Use:
```bash
grep -r "ValueError" tests/ | grep -i "checkpoint\|understand"
```

## Failure modes

### Failure mode 1: Import cycle

**Detection**: `ImportError` when running any test that imports evaluate/worker.py
**Resolution**: `launcher.util.errors` imports nothing from launcher — no cycle possible
**Gate**: unit tests

### Failure mode 2: Test asserts wrong exception type

**Detection**: `pytest.raises(ValueError)` tests fail with `WorkerError`
**Resolution**: Update assertion to `WorkerError` or `LaunchError`
**Gate**: unit tests

### Failure mode 3: Orchestrator catches WorkerError differently

**Detection**: Pipeline run fails with unhandled `WorkerError`
**Resolution**: `WorkerError` inherits `LaunchError(RuntimeError)` — caught by all generic `except Exception` handlers in run_loop.py
**Gate**: integration tests

## Task-specific review checklist

1. [ ] `WorkerError` defined in `errors.py` with correct parent `LaunchError`
2. [ ] `_load_understand_checkpoint` raises `WorkerError` (both raise sites)
3. [ ] `_assert_understand_checkpoint` raises `WorkerError`
4. [ ] `WorkerError` imported in both files
5. [ ] No tests asserting `ValueError` from these functions remain
6. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — all pass
7. [ ] Docstrings updated for `_load_understand_checkpoint` (Raises: WorkerError)
8. [ ] No spec drift — errors.py is not a spec file
9. [ ] Schema: no schema changes needed
10. [ ] Checked docs/README.md — no ownership trigger
11. [ ] No new docs/guides/ file added

## Deliverables

1. Updated `src/launcher/util/errors.py` with `WorkerError` class
2. Updated `evaluate/worker.py` and `run_loop.py` with `WorkerError` raises
3. Evidence at `reports/agents/TC-GAP-01/evidence.md`

## Acceptance checks

1. [x] `grep -n "WorkerError" src/launcher/util/errors.py` shows class definition
2. [x] `grep -n "WorkerError" src/launcher/workers/evaluate/worker.py` shows import + 2 raise sites
3. [x] `grep -n "WorkerError" src/launcher/orchestrator/run_loop.py` shows import + 2 raise sites
4. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — 3816/3816 pass, 0 failures

## Self-review

### Verification results
- [x] Tests: 3816/3816 PASS
- [x] Evidence captured: reports/agents/TC-GAP-01/evidence.md

## E2E verification

```bash
grep -n "WorkerError" src/launcher/util/errors.py
grep -n "WorkerError" src/launcher/workers/evaluate/worker.py
grep -n "WorkerError" src/launcher/orchestrator/run_loop.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q
```

## Integration boundary proven

**Upstream**: `_load_understand_checkpoint` is called from evaluate/worker.py's execute()
**Downstream**: `WorkerError` propagates to orchestrator's generic `except Exception` handler
**Contract**: `WorkerError(LaunchError(RuntimeError))` — caught by all existing handlers
