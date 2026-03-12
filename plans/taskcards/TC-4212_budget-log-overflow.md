---
id: TC-4212
title: "Budget log overflow — dropped_by_category tracking"
status: Done
priority: Normal
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [scout, observability, budget]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4212_budget-log-overflow.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout_budget_log_cap.py
  - reports/agents/wave1/TC-4212/evidence.md
evidence_required:
  - reports/agents/wave1/TC-4212/evidence.md
---

# Taskcard TC-4212 — Budget log overflow — dropped_by_category tracking

## Objective

When `budget_log` overflows past `_BUDGET_LOG_MAX = 500`, the overflow entries
are currently counted but their skip-reason identity is lost. This taskcard adds
a `dropped_by_category` dict that counts dropped entries by their `reason` field,
and emits a structured WARNING so operators can see which skip categories are most
common in large repos without storing thousands of entries.

## Required spec references

- `specs/worker_understand.md` (Section: Scout budget management and observability)

## Scope

### In scope
- Build `dropped_by_category: dict[str, int]` from overflow entries before discarding them
- Store it in the `_read_repo_content` return tuple (extend return type)
- Emit a single `logger.warning(...)` on first overflow
- Update `run_scout` to thread `dropped_by_category` through to its log message
- Unit tests: 600 entries → verify `dropped_by_category` present, counts correct, WARNING logged

### Out of scope
- Raising `_BUDGET_LOG_MAX` beyond 500
- Persisting `dropped_by_category` to disk artifacts
- Changes to the scout output model schema

## Inputs

- `src/launcher/workers/scout/scout.py` (current implementation)

## Outputs

- `src/launcher/workers/scout/scout.py` (patched)
- `tests/unit/workers/test_scout_budget_log_cap.py` (new tests for TC-4212)
- `reports/agents/wave1/TC-4212/evidence.md`

## Allowed paths

- plans/taskcards/TC-4212_budget-log-overflow.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout_budget_log_cap.py
- reports/agents/wave1/TC-4212/evidence.md

### Allowed paths rationale
- `scout.py`: site of the budget log overflow logic
- `test_scout_budget_log_cap.py`: existing test file for budget log behavior
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Add `dropped_by_category` tracking to `_read_repo_content`

Inside each `budget_log_overflow += 1` branch, also update a local
`dropped_by_category: dict[str, int]` dict:
- For entries that have a `"reason"` key: `dropped_by_category[reason] = dropped_by_category.get(reason, 0) + 1`
- For entries that don't have a reason (e.g. truncated files): use key `"unknown"`

At the first overflow, emit:
```python
if budget_log_overflow == 1:
    logger.warning(
        "[Scout] Budget log truncated at %d entries. "
        "Additional entries will be counted in dropped_by_category.",
        _BUDGET_LOG_MAX,
    )
```

### Step 2: After the main loop, emit summary WARNING

```python
if budget_log_overflow > 0:
    logger.warning(
        "[Scout] Budget log overflow: %d entries dropped. "
        "Dropped categories: %s",
        budget_log_overflow,
        dropped_by_category,
    )
```

### Step 3: Update return type

Change the function signature return annotation and the actual return statement to
include `dropped_by_category`:
- Return: `tuple[dict[str,str], int, int, list[dict], int, dict[str,int]]`

### Step 4: Update `run_scout` caller

Update the unpacking in `run_scout`:
```python
repo_content, sanitize_redactions, sanitize_truncated, budget_log, budget_log_overflow, dropped_by_category = _read_repo_content(...)
```
And add `dropped_by_category` to the logger.info call.

### Step 5: Write tests

Add `TestDroppedByCategory` class in `test_scout_budget_log_cap.py`:
- `test_dropped_by_category_present`: 600 files → `dropped_by_category` is dict
- `test_dropped_by_category_counts_correct`: verify total count matches `budget_log_overflow`
- `test_warning_logged_on_overflow`: use `caplog` to verify WARNING message

## Failure modes

### Failure mode 1: Callers unpacking 5-tuple break after adding 6th element

**Detection**: `ValueError: not enough values to unpack` in `run_scout` or tests
**Resolution**: Update all callers of `_read_repo_content` to unpack 6 values
**Gate**: `test_budget_log_never_exceeds_500` fails

### Failure mode 2: `dropped_by_category` key determination wrong for truncated entries

**Detection**: Truncated entries (reason `per_file_cap`) have no consistent key
**Resolution**: The truncated-entry branch doesn't pass a `reason` at the log level; use `"per_file_cap"` as a known fallback key
**Gate**: `test_dropped_by_category_counts_correct` fails if total doesn't match

### Failure mode 3: WARNING emitted more than once per overflow batch

**Detection**: Log flooding with repeated warnings on every overflow entry
**Resolution**: Emit only on `budget_log_overflow == 1` (first overflow) and once more as summary at end of function
**Gate**: `test_warning_logged_on_overflow` check count

## Task-specific review checklist

1. [ ] `dropped_by_category` dict built before any overflow is discarded
2. [ ] WARNING emitted on first overflow (not every overflow)
3. [ ] Summary WARNING emitted at end of function when overflow > 0
4. [ ] Return type updated to 6-tuple
5. [ ] `run_scout` unpacking updated
6. [ ] Three new tests present and passing
7. [ ] Docstring for `_read_repo_content` updated to document the 6-tuple
8. [ ] Spec file confirmed — no drift introduced
9. [ ] Schema — no change required (dropped_by_category is runtime-only)
10. [ ] `docs/README.md` ownership map checked — no guide update needed
11. [ ] Existing `TestBudgetLogCap` tests still pass

## Deliverables

1. Patched `src/launcher/workers/scout/scout.py`
2. Updated `tests/unit/workers/test_scout_budget_log_cap.py` with three new tests
3. `reports/agents/wave1/TC-4212/evidence.md`

## Acceptance checks

1. [ ] All existing `TestBudgetLogCap` tests pass
2. [ ] `TestDroppedByCategory` has 3 passing tests
3. [ ] WARNING logged on overflow (verified via caplog)

## Self-review

### Verification results
- [ ] Tests: 3/3 PASS (TestDroppedByCategory) + 4/4 PASS (TestBudgetLogCap)
- [ ] Validation: overflow tracking correct
- [ ] Evidence captured: reports/agents/wave1/TC-4212/evidence.md
- [ ] Doc freshness: no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_budget_log_cap.py -x -v
```

**Expected results**:
- All TestBudgetLogCap tests pass (regression)
- All TestDroppedByCategory tests pass

## Integration boundary proven

**Upstream**: `_walk_file_tree` provides file_index to `_read_repo_content`
**Downstream**: `run_scout` returns `(repo_info, repo_content, budget_log, budget_log_overflow)` to callers
**Contract**: `budget_log` is capped at 500; overflow entries are counted in `budget_log_overflow`; skip-reason distribution available in `dropped_by_category`
