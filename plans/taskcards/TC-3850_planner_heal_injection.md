---
id: TC-3850
title: "Planner Worker Heal Directive Injection (H3.3)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, planner]
depends_on: [TC-3841, TC-3834]
allowed_paths:
  - plans/taskcards/TC-3850_planner_heal_injection.md
  - src/launcher/workers/planner/worker.py
  - tests/unit/workers/test_planner_heal.py
evidence_required:
  - reports/TC-3850/evidence.md
---

# Taskcard TC-3850 — Planner Worker Heal Directive Injection (H3.3)

## Objective

Add heal directive reading to `PlannerWorker.run()` so that when the heal CLI
re-runs with `re_run_count > 0`, the planner redistributes claims based on
`heal_metadata.failed_checks` and emits a `planner_heal_mode` event.

## Required spec references

- `specs/heal.md` (heal directive injection contract)

## Scope

### In scope
- Read `heal_metadata = context.heal_metadata` at start of `run()`
- If `re_run_count > 0`, emit `planner_heal_mode` event with failed_checks
- Log heal mode notice with page roles that need healing
- NOTE: TC-3834 already modified planner/worker.py for golden self-review — verify it's present
- No changes to `run_plan()` itself — this is a preparatory injection point

### Out of scope
- Actually modifying claim redistribution in run_plan() — requires deeper planner refactor
- Heal CLI setting heal_metadata (TC-3851)

## Inputs

- `src/launcher/workers/planner/worker.py` (185 lines, TC-3834 Done first)
- `context.heal_metadata` dict from WorkerContext (TC-3841 Done)

## Outputs

- `planner_heal_mode` event emitted when re_run_count > 0
- Log message indicating which pages need healing

## Allowed paths

- plans/taskcards/TC-3850_planner_heal_injection.md
- src/launcher/workers/planner/worker.py
- tests/unit/workers/test_planner_heal.py

### Allowed paths rationale

Only planner worker modified (TC-3834 Done first); one new test file.

## Implementation steps

### Step 1: Verify TC-3834 golden self-review is present

Read `planner/worker.py` and confirm the golden self-review block (lines ~52-90) is present.
If absent, this TC cannot proceed — TC-3834 must be verified Done first.

### Step 2: Read heal_metadata at start of run()

At the beginning of `run()`, BEFORE the `run_plan()` call (after `bundle = input_data`):
```python
# Heal mode: read directives from heal_metadata if present
heal_metadata: dict = context.heal_metadata or {}
re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
if re_run_count > 0:
    failed_pages = heal_metadata.get("failed_pages", []) or []
    failed_checks = heal_metadata.get("failed_checks", []) or []
    context.log.info(
        "[Planner] Heal mode (re_run=%d): %d pages need healing, checks: %s",
        re_run_count, len(failed_pages), failed_checks,
    )
    context.emit_event(
        "planner_heal_mode",
        {
            "re_run_count": re_run_count,
            "failed_pages": failed_pages,
            "failed_checks": failed_checks,
        },
        worker=self.name,
    )
```

### Step 3: Add tests

`tests/unit/workers/test_planner_heal.py`:
- heal_metadata={} → no `planner_heal_mode` event emitted
- heal_metadata={"re_run_count": 1} → `planner_heal_mode` event with re_run_count=1
- heal_metadata={"re_run_count": 1, "failed_pages": ["pg-1"], "failed_checks": ["density"]}
  → event has failed_pages and failed_checks
- re_run_count=0 → no event (normal run)
- Golden self-review block still present (regression check)

## Failure modes

### Failure mode 1: TC-3834 golden self-review block missing

**Detection**: Golden self-review block (GoldenIndex load) absent from planner/worker.py
**Resolution**: Verify TC-3834 evidence file; if Done, re-read the file — it must be present
**Gate**: Read planner/worker.py and grep for GoldenIndex import

### Failure mode 2: context.heal_metadata is None

**Detection**: `NoneType` access error
**Resolution**: `heal_metadata = context.heal_metadata or {}` — coerces None to dict
**Gate**: Unit test with heal_metadata=None

### Failure mode 3: run_plan() signature conflict

**Detection**: Any modification to run_plan() call fails
**Resolution**: This TC does NOT modify run_plan() — only adds injection point BEFORE the call
**Gate**: All existing planner tests still pass

## Task-specific review checklist

1. [ ] `planner_heal_mode` event emitted only when re_run_count > 0
2. [ ] `planner_heal_mode` event has keys: re_run_count, failed_pages, failed_checks
3. [ ] Normal run (heal_metadata={}) produces no `planner_heal_mode` event
4. [ ] TC-3834 golden self-review block still present (verified by reading the file)
5. [ ] `run_plan()` call unchanged (no extra kwargs)
6. [ ] All 5 tests pass

## Deliverables

1. `src/launcher/workers/planner/worker.py` — heal_metadata reading + event emission
2. `tests/unit/workers/test_planner_heal.py` — 5 test cases
3. `reports/TC-3850/evidence.md` — actual test output

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_planner_heal.py -v` — 5/5 PASS
2. [x] `planner_heal_mode` event emitted for re_run_count > 0
3. [x] `pytest tests/ -q` — 0 failures (2488 passed)

## Self-review

### Verification results
- [x] Tests: 5/5 PASS
- [x] Validation: event emitted in heal mode, silent in normal mode
- [x] Evidence file: `reports/TC-3850/evidence.md`
- [x] TC-3834 golden self-review block verified present (GoldenIndex importable)
- [x] Full suite: 2488 passed, 0 failed

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_planner_heal.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 5 planner heal tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `context.heal_metadata` from WorkerContext (TC-3841); TC-3834 golden self-review already present
**Downstream**: Heal CLI (TC-3851) sets heal_metadata before re-running planner worker
**Contract**: `planner_heal_mode` event has `{re_run_count: int, failed_pages: list, failed_checks: list}`
