---
id: TC-3869
title: "Fix resume mechanism: skip workers with cached outputs in worker_outputs"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [resume, heal, orchestrator, bugfix]
depends_on: [TC-3840, TC-3797]
allowed_paths:
  - plans/taskcards/TC-3869_resume_skip_cached_workers.md
  - src/launcher/orchestrator/graph_builder.py
  - tests/unit/orchestrator/test_graph_builder.py
evidence_required:
  - reports/TC-3869/evidence.md
---

# Taskcard TC-3869 — Fix resume mechanism: skip workers with cached outputs

## Objective

Add a skip guard in `_make_worker_node`'s `_node()` so that workers whose output already
exists in `state["worker_outputs"]` (loaded by `_build_resume_state`) return early without
re-executing. This makes `--resume-from` work correctly for both direct CLI resume and the
heal loop, which calls `execute_run(resume_from=worker)` on every heal step.

## Required spec references

- `specs/06_orchestrator_run_loop.md` (resume_from semantics)

## Scope

### In scope
- Add one skip guard block in `_make_worker_node._node()` in `graph_builder.py`
- Add unit tests for: skip on cached output, no-skip on empty cache, partial resume, no-skip on re-run

### Out of scope
- Modifying `_build_resume_state()` — it already loads the right data
- Modifying `_find_input_data()` — it already reads from `worker_outputs`
- Modifying `heal.py` or `__heal_router__` — the bypass stays as an optimization
- Fixing `resume_from` validation (missing worker name check) — separate issue
- Fixing checkpoint coherence for heal bypass — separate issue

## Inputs

- `src/launcher/orchestrator/graph_builder.py` (existing `_make_worker_node` at line 170)
- `src/launcher/orchestrator/state.py` (`PipelineGraphState` including `worker_outputs`, `re_run_count`)

## Outputs

- `graph_builder.py` with skip guard in `_node()`
- `test_graph_builder.py` with 4 new test cases

## Allowed paths

- plans/taskcards/TC-3869_resume_skip_cached_workers.md
- src/launcher/orchestrator/graph_builder.py
- tests/unit/orchestrator/test_graph_builder.py

### Allowed paths rationale

`graph_builder.py` is the only file that needs the skip guard. Tests go in the existing
`test_graph_builder.py` which already has fixtures for this module.

## Implementation steps

### Step 1: Add skip guard in `graph_builder.py`

In `_make_worker_node._node()`, after line 209 (`ctx = WorkerContext(...)` fully constructed),
insert before the existing `if state["errors"]:` block at line 211:

```python
        # -- skip if output already cached (resume mode, first pass only) -------
        # re_run_count > 0 means evaluate triggered a re-run loop — in that case
        # worker_outputs may still hold a stale first-pass output so we MUST NOT
        # skip: the re-run target (e.g. generate) needs to produce fresh output.
        if state.get("re_run_count", 0) == 0 and worker_name in (state.get("worker_outputs") or {}):
            logger.info(
                "[%s] Skipping %s — cached output found in worker_outputs",
                state["run_id"], worker_name,
            )
            ctx.emit_event(
                "worker_skipped",
                {"worker": worker_name, "reason": "resume_checkpoint"},
                worker=worker_name,
            )
            return {"current_worker": worker_name}

```

### Step 2: Add tests in `test_graph_builder.py`

Add a new test class `TestResumeSkipCachedWorkers` with 4 test cases:

1. **`test_worker_skipped_when_output_cached`**: pre-populate `worker_outputs["dummy"]` in
   initial state with `re_run_count=0`; assert `worker.run` is NOT called; assert
   `worker_skipped` event is emitted in the events file.

2. **`test_worker_runs_when_output_not_cached`**: empty `worker_outputs`, `re_run_count=0`;
   assert `worker.run` IS called and output written to `worker_outputs`.

3. **`test_worker_runs_on_rerun_despite_cached_output`**: pre-populate `worker_outputs["dummy"]`
   with `re_run_count=1`; assert `worker.run` IS called (re-run must not be skipped).

4. **`test_partial_resume_two_workers`** (if two-worker pipeline is feasible in the test
   fixture): A output cached, B not; assert A skipped, B runs; final `worker_outputs` has both.

## Failure modes

### Failure mode 1: Skip fires during re-run (wrong `re_run_count` check)

**Detection**: Generate worker skipped on re-run iteration; evaluate never gets fresh output;
`worker_skipped` event emitted with `reason: resume_checkpoint` when `re_run_count > 0`.
**Resolution**: Verify the guard reads `state.get("re_run_count", 0) == 0` not just
`worker_name in worker_outputs`.
**Gate**: Unit test `test_worker_runs_on_rerun_despite_cached_output`

### Failure mode 2: Event emission fails because ctx not built

**Detection**: `AttributeError` or similar from `ctx.emit_event`; or `NameError: ctx`.
**Resolution**: Ensure the skip block is placed AFTER line 209 (after `ctx = WorkerContext(...)`).
**Gate**: Unit test `test_worker_skipped_when_output_cached` verifies event is written.

### Failure mode 3: LangGraph does not merge state correctly

**Detection**: Downstream worker's `_find_input_data` returns `state["config"]` instead of
predecessor's output (i.e., `worker_outputs` appears empty to next worker).
**Resolution**: Verify return is `{"current_worker": worker_name}` only — do NOT return
`{"worker_outputs": ...}` which would replace the full dict.
**Gate**: Unit test `test_partial_resume_two_workers`

## Task-specific review checklist

1. [ ] Skip guard placed AFTER ctx build, BEFORE `if state["errors"]:` check
2. [ ] Condition includes both `re_run_count == 0` AND `worker_name in worker_outputs`
3. [ ] `worker_skipped` event emitted with `reason: "resume_checkpoint"`
4. [ ] Return dict contains ONLY `{"current_worker": worker_name}` — not worker_outputs
5. [ ] Test: skip fires when `re_run_count=0` and output cached
6. [ ] Test: skip does NOT fire when `re_run_count=1` even if output cached
7. [ ] Test: skip does NOT fire when `worker_outputs` is empty
8. [ ] All existing `test_graph_builder.py` tests still pass
9. [ ] Docstrings updated for `_make_worker_node` to document resume skip behavior
10. [ ] Spec file updated if worker behavior changed (confirmed: no spec drift, behavior
        matches intended resume semantics already described in spec)
11. [ ] Schema `"description"` fields: no new schema properties added
12. [ ] Checked `docs/README.md` ownership map — no guide update triggered

## Deliverables

1. `src/launcher/orchestrator/graph_builder.py` — skip guard in `_node()` (~15 lines)
2. `tests/unit/orchestrator/test_graph_builder.py` — 4 new test cases in `TestResumeSkipCachedWorkers`
3. `reports/TC-3869/evidence.md` — test output showing all tests pass

## Acceptance checks

1. [x] `pytest tests/unit/orchestrator/test_graph_builder.py -v` — 0 failures, 5 new tests pass
2. [x] `worker_skipped` event emitted with `reason: resume_checkpoint` (verified in test)
3. [x] Re-run iteration does NOT skip generate (verified by `test_worker_runs_on_rerun_despite_cached_output`)
4. [x] `pytest tests/ -x -q` — 3073 passed, 0 failures (full suite)

## Self-review

### Verification results
- [x] Tests: 5/5 new PASS + 3073/3073 full suite PASS
- [x] Validation: worker_skipped(reason=resume_checkpoint) event verified in test
- [x] Evidence captured: reports/TC-3869/evidence.md
- [x] Doc freshness: no spec drift (behavior matches intended resume semantics)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 4 new tests in `TestResumeSkipCachedWorkers` pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `_build_resume_state()` populates `state["worker_outputs"]` with checkpoint data
before the graph executes
**Downstream**: `_find_input_data()` reads from `state["worker_outputs"]` to resolve worker input
**Contract**: `state["worker_outputs"][worker_name]` is a `dict[str, Any]` matching the worker's
output schema; LangGraph merges partial state returns so existing keys are preserved
