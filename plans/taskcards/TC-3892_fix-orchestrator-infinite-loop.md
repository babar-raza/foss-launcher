---
id: TC-3892
title: "Fix Orchestrator Infinite Loop After Evaluate on NO_GO Verdict"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [orchestrator, graph_builder, bug, infinite-loop, re-run]
depends_on: []
allowed_paths:
  - src/launcher/orchestrator/graph_builder.py
  - tests/test_graph_builder.py
---

## Objective

Fix two related bugs in `graph_builder.py` that cause the pipeline to spin in
an infinite loop after `evaluate` returns `NO_GO`:

1. **Wrong path_map target**: The conditional edges from `evaluate` map the
   `"__re_run__"` return value directly to `re_run_first_target` (e.g.
   `"understand"`), bypassing the `__re_run__` increment node. So
   `re_run_count` is never incremented, the skip guard
   `re_run_count == 0 and _cached_output is not None` fires on every worker,
   and all workers skip indefinitely.

2. **max_re_runs not read from topology**: `_should_re_run` reads
   `state.get("max_re_runs", 2)`, but `run_loop.py` always initialises the
   state with `max_re_runs=2`, ignoring the `max_re_runs: 0` in
   `pipeline.yaml`. With `max_re_runs=0` the re-run loop should never trigger.

## Root Cause

**Bug 1** — `graph_builder.py` lines 644–650:
```python
graph.add_conditional_edges(
    wname,
    _should_re_run,
    {
        "publish": ...,
        "__re_run__": re_run_first_target or END,  # WRONG: bypasses __re_run__ node
        END: END,
    },
)
```
Should be `"__re_run__": "__re_run__"` so the increment node is visited.

**Bug 2** — `_should_re_run` (module-level function) reads `max_re_runs` from
state. `run_loop.py` always sets `max_re_runs=2` regardless of the pipeline
YAML value. Moving `_should_re_run` inside `build_pipeline` as a closure
lets it capture `evaluate_entry.max_re_runs` directly.

## Scope

### In scope
- `graph_builder.py` — fix path_map and `_should_re_run` closure
- Unit test for the routing logic

### Out of scope
- `run_loop.py` — no changes needed (max_re_runs state field can remain for
  future use; the closure approach makes it irrelevant)

## Inputs
- `src/launcher/orchestrator/graph_builder.py` (current)

## Outputs
- Fixed `graph_builder.py`
- Pipeline terminates at END after evaluate returns NO_GO when max_re_runs=0

## Allowed paths
- src/launcher/orchestrator/graph_builder.py
- tests/test_graph_builder.py

### Allowed paths rationale
Both bugs are in `graph_builder.py`. A test exists (or needs to exist) that
exercises the conditional routing logic.

## Implementation steps

### Step 1: Fix conditional edge path_map

In `build_pipeline`, change the `add_conditional_edges` call for `evaluate`:

```python
# BEFORE (bug — bypasses __re_run__ node):
"__re_run__": re_run_first_target or END,

# AFTER (correct — routes through increment node first):
"__re_run__": "__re_run__",
```

### Step 2: Move _should_re_run inside build_pipeline as a closure

Remove the module-level `_should_re_run` function. Inside `build_pipeline`,
after `evaluate_entry` is identified, define:

```python
_max_re_runs_cfg = evaluate_entry.max_re_runs if evaluate_entry else 0

def _should_re_run(state: PipelineGraphState) -> str:
    verdict = state.get("verdict", "")
    re_run_count = state.get("re_run_count", 0)
    if verdict == "GO":
        return "publish"
    if re_run_count < _max_re_runs_cfg and verdict == "NO_GO":
        return "__re_run__"
    return END
```

This captures `max_re_runs` from the `WorkerEntry` (parsed from pipeline.yaml)
so the state field is irrelevant.

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Failure modes

### Failure mode 1: `__re_run__` node not in graph

**Detection**: `KeyError: '__re_run__'` when building conditional edges if
`evaluate_entry` is None (pipeline without evaluate worker).
**Resolution**: Guard: only add `"__re_run__": "__re_run__"` key if
`evaluate_entry is not None and re_run_first_target`.
**Gate**: `build_pipeline` must not crash for minimal pipelines.

### Failure mode 2: Closure captures wrong value

**Detection**: Unit test for `_should_re_run` returns wrong route.
**Resolution**: Verify that `evaluate_entry.max_re_runs` is the value from
pipeline.yaml (0 in the current config).
**Gate**: Unit test asserts NO_GO with re_run_count=0 returns END when
max_re_runs=0.

### Failure mode 3: Re-run loop never fires when max_re_runs > 0

**Detection**: With max_re_runs=1, NO_GO verdict, re_run_count=0 →
`_should_re_run` should return `"__re_run__"`.
**Resolution**: Verify closure variable is set correctly from entry.
**Gate**: Unit test covers this path.

## Task-specific review checklist

1. [ ] `"__re_run__": "__re_run__"` in path_map (not `re_run_first_target`)
2. [ ] `_should_re_run` reads `max_re_runs` from closure, not state
3. [ ] `evaluate_entry` is not None before defining the closure
4. [ ] Full pipeline test: NO_GO verdict with max_re_runs=0 → graph terminates
5. [ ] `test_graph_builder.py` tests updated/added for both routing paths
6. [ ] All existing tests pass
7. [ ] Docstrings updated for `build_pipeline`
8. [ ] Spec file confirmed no drift (orchestrator is internal)
9. [ ] Schema description fields confirmed unchanged
10. [ ] Checked `docs/README.md` — no trigger event applies
11. [ ] No new docs/guides/ files needed

## Deliverables

1. Fixed `src/launcher/orchestrator/graph_builder.py`
2. Passing test suite

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass
2. [ ] With `max_re_runs=0`, NO_GO verdict routes to END (not `"__re_run__"`)
3. [ ] With `max_re_runs=1`, NO_GO verdict re_run_count=0 routes to `"__re_run__"` node
4. [ ] Fresh pilot run terminates after evaluate (no infinite loop in log)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: pilot run log shows no looping
- [ ] Doc freshness: no drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Then: pilot run should terminate cleanly
grep "Skipping.*cached output" runs/<new_run>/events.ndjson | wc -l
# Should be 0 or very small (only resume skips, no re-run skips)
```

## Integration boundary proven

**Upstream**: `evaluate` worker emits `verdict=NO_GO` into graph state
**Downstream**: `_should_re_run` routes to `END` (or `__re_run__` for future re-runs)
**Contract**: After evaluate, graph terminates when max_re_runs=0
