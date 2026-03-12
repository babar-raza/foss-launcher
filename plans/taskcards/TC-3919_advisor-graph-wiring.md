---
id: TC-3919
title: "Wire PipelineAdvisor LLM routing node into LangGraph pipeline"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [orchestrator, langgraph, advisor, routing]
depends_on: [TC-3918]
allowed_paths:
  - plans/taskcards/TC-3919_advisor-graph-wiring.md
  - src/launcher/orchestrator/state.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/orchestrator/graph_builder.py
  - configs/pipeline.yaml
  - tests/unit/orchestrator/test_advisor_routing.py
evidence_required:
  - reports/TC-3919/evidence.md
---

# Taskcard TC-3919 — Wire PipelineAdvisor LLM routing node into LangGraph pipeline

## Objective

Wire the `PipelineAdvisor` (TC-3918) as a LangGraph node (`__advisor__`) that replaces the static `_make_should_re_run` router after evaluate emits `NO_GO`. The advisor calls the LLM routing module to decide whether to re-generate, publish, or stop — enabling intelligent post-evaluate routing with ceiling enforcement.

## Required spec references

- `specs/orchestrator.md` (Section: pipeline routing, re-run control)
- `specs/evaluate.md` (Section: verdict handling, re-run triggers)
- `src/launcher/orchestrator/pipeline_advisor.py` (TC-3918: advisor module being wired)

## Scope

### In scope
- Add `advisor_decision` field to `PipelineGraphState` TypedDict
- Add `advisor_decision={}` to both `PipelineGraphState(...)` constructor calls in `run_loop.py`
- Add `_make_post_evaluate_router()` module-level function to `graph_builder.py`
- Add `_make_advisor_route()` module-level function to `graph_builder.py`
- Replace `_should_re_run` with `_post_evaluate_router` in `build_pipeline()`
- Add `__advisor__` async node in `build_pipeline()` (conditional on max_re_runs > 0)
- Update evaluate conditional edges to route to `__advisor__` instead of `__re_run__`
- Set `re_run_targets: [generate]` and `max_re_runs: 2` in `configs/pipeline.yaml`
- Write 3 test classes in `tests/unit/orchestrator/test_advisor_routing.py`

### Out of scope
- `heal_upstream` routing path (excluded in v1, noted in `_make_advisor_route` docstring)
- Changes to `pipeline_advisor.py` itself (TC-3918)
- Changes to worker implementations
- UI/CLI changes

## Inputs

- `src/launcher/orchestrator/state.py` — existing PipelineGraphState TypedDict
- `src/launcher/orchestrator/run_loop.py` — execute_run and _build_resume_state
- `src/launcher/orchestrator/graph_builder.py` — existing _make_should_re_run, build_pipeline
- `configs/pipeline.yaml` — pipeline topology with evaluate config
- `src/launcher/orchestrator/pipeline_advisor.py` — TC-3918 advisor module

## Outputs

- Updated `src/launcher/orchestrator/state.py` with `advisor_decision` field
- Updated `src/launcher/orchestrator/run_loop.py` with `advisor_decision={}` in both constructors
- Updated `src/launcher/orchestrator/graph_builder.py` with advisor node and new routing functions
- Updated `configs/pipeline.yaml` with `re_run_targets: [generate]`, `max_re_runs: 2`
- New `tests/unit/orchestrator/test_advisor_routing.py` with 3 test classes

## Allowed paths

- plans/taskcards/TC-3919_advisor-graph-wiring.md
- src/launcher/orchestrator/state.py
- src/launcher/orchestrator/run_loop.py
- src/launcher/orchestrator/graph_builder.py
- configs/pipeline.yaml
- tests/unit/orchestrator/test_advisor_routing.py

### Allowed paths rationale

- `state.py`: Adding `advisor_decision` field to state TypedDict
- `run_loop.py`: Updating PipelineGraphState constructors in _build_resume_state and execute_run
- `graph_builder.py`: Adding advisor node, new router functions, wiring conditional edges
- `configs/pipeline.yaml`: Setting max_re_runs=2 and re_run_targets=[generate]
- `tests/unit/orchestrator/test_advisor_routing.py`: New test file for routing logic

## Implementation steps

### Step 1: Add `advisor_decision` to PipelineGraphState

In `state.py`, add `advisor_decision: dict[str, Any]` field after `heal_metadata`.
`Any` is already imported.

### Step 2: Update _build_resume_state constructor

In `run_loop.py`, find the `PipelineGraphState(...)` call in `_build_resume_state()`.
Add `advisor_decision={}` argument.

### Step 3: Update execute_run constructor

In `run_loop.py`, find the `PipelineGraphState(...)` call in `execute_run()`.
Add `advisor_decision={}` argument.

### Step 4: Add _make_post_evaluate_router to graph_builder.py

Insert module-level function after `_make_should_re_run()`, before `_verdict_gate()`.
Routes GO->publish, NO_GO+budget->__advisor__, else->END.

### Step 5: Add _make_advisor_route to graph_builder.py

Insert module-level function immediately after `_make_post_evaluate_router()`.
Routes advisor_decision.routing: heal_generate->__re_run__, publish->publish/END, else->END.

### Step 6: Replace _should_re_run with _post_evaluate_router in build_pipeline

Find and replace the `_should_re_run = _make_should_re_run(...)` assignment.
Replace with `_post_evaluate_router = _make_post_evaluate_router(...)`.

### Step 7: Add __advisor__ node in build_pipeline

After worker-node building loop, add conditional block for max_re_runs > 0.
Add async `_advisor_node` calling `call_pipeline_advisor` or `_static_fallback`.
Register with `graph.add_node("__advisor__", _advisor_node)`.
Wire conditional edges from `__advisor__` using `_make_advisor_route`.

### Step 8: Update evaluate conditional edges

Replace `_should_re_run` with `_post_evaluate_router` in `add_conditional_edges`.
Build edge map conditionally: include `__advisor__` only when max_re_runs > 0.

### Step 9: Update configs/pipeline.yaml

Change `re_run_targets: [understand, generate]` to `re_run_targets: [generate]`.
Change `max_re_runs: 0` to `max_re_runs: 2`.

### Step 10: Write test file

Create `tests/unit/orchestrator/test_advisor_routing.py` with 3 test classes:
- `TestPostEvaluateRouter` (4 tests)
- `TestAdvisorRoute` (5 tests)
- `TestPipelineYamlReRunConfig` (2 tests)

### Step 11: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_advisor_routing.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -20
```

## Failure modes

### Failure mode 1: __advisor__ key in edge map with no node

**Detection**: `ValueError: Node __advisor__ not found in graph` during `build_pipeline()`
**Resolution**: Ensure `_edge_map["__advisor__"] = "__advisor__"` is only set when `evaluate_entry is not None and evaluate_entry.max_re_runs > 0` (same condition as node registration)
**Gate**: Graph compilation guard

### Failure mode 2: advisor_decision missing from PipelineGraphState

**Detection**: `KeyError: advisor_decision` in `_advisor_node` or state access; TypedDict strict mode failure
**Resolution**: Verify `advisor_decision: dict[str, Any]` is present in TypedDict and `advisor_decision={}` is in both constructors
**Gate**: Python type checking / runtime dict access

### Failure mode 3: Import cycle in _advisor_node

**Detection**: `ImportError: cannot import name 'call_pipeline_advisor'` at runtime
**Resolution**: Keep imports inside the `_advisor_node` closure (lazy import pattern already used in graph_builder for other deferred imports)
**Gate**: Module import checks

### Failure mode 4: _make_post_evaluate_router not importable by tests

**Detection**: `ImportError` in test file trying to import `_make_post_evaluate_router`
**Resolution**: Ensure both functions are placed at module level (not nested inside build_pipeline)
**Gate**: Test collection failure

### Failure mode 5: re_run_count never increments with new routing

**Detection**: Infinite loop; evaluate runs repeatedly without incrementing count
**Resolution**: `__advisor__` routes to `__re_run__` (not directly to generate) which increments re_run_count before re-entering generate
**Gate**: TC-3892 regression (infinite loop prevention)

## Task-specific review checklist

1. [ ] `advisor_decision: dict[str, Any]` present in `PipelineGraphState` TypedDict
2. [ ] Both `PipelineGraphState(...)` constructor calls in `run_loop.py` include `advisor_decision={}`
3. [ ] `_make_post_evaluate_router` is a module-level function (importable by tests)
4. [ ] `_make_advisor_route` is a module-level function (importable by tests)
5. [ ] `__advisor__` node only registered when `max_re_runs > 0` (avoids dead key in edge map)
6. [ ] `"__advisor__"` key in evaluate edge map only added when `max_re_runs > 0`
7. [ ] `__advisor__` routes to `__re_run__` (not generate directly) — preserves re_run_count increment
8. [ ] `configs/pipeline.yaml` has `re_run_targets: [generate]` and `max_re_runs: 2`
9. [ ] Docstrings updated for `_make_post_evaluate_router` and `_make_advisor_route`
10. [ ] All 11 tests in `test_advisor_routing.py` pass
11. [ ] Full test suite passes (`tests/ -x -q`)

## Deliverables

1. Updated `src/launcher/orchestrator/state.py`
2. Updated `src/launcher/orchestrator/run_loop.py`
3. Updated `src/launcher/orchestrator/graph_builder.py`
4. Updated `configs/pipeline.yaml`
5. New `tests/unit/orchestrator/test_advisor_routing.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_advisor_routing.py -v` — 11/11 PASS
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass, no regressions
3. [ ] `_make_post_evaluate_router` and `_make_advisor_route` importable from `launcher.orchestrator.graph_builder`
4. [ ] `PipelineGraphState` has `advisor_decision` field
5. [ ] `configs/pipeline.yaml` evaluate entry has `max_re_runs: 2` and `re_run_targets: [generate]`

## Self-review

### Verification results
- [x] Tests: 11/11 PASS (test_advisor_routing.py)
- [x] Full suite: 3316 passed, 1 skipped, 3 xfailed (no regressions)
- [x] Validation: graph compilation PASS
- [x] Evidence captured: pytest output
- [x] Doc freshness: acknowledged (orchestrator internals, no public spec change)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_advisor_routing.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -20
```

**Expected results**:
- All 11 advisor routing tests pass
- Full suite passes with no regressions

## Integration boundary proven

**Upstream**: `evaluate` worker emits `verdict=NO_GO` into `PipelineGraphState`
**Downstream**: `__advisor__` node reads `worker_outputs["evaluate"]`, calls `call_pipeline_advisor`, writes `advisor_decision` back to state; `_make_advisor_route` routes to `__re_run__`, `publish`, or `END`
**Contract**: `PipelineAdvice` Pydantic model (TC-3918) serialised into `advisor_decision: dict[str, Any]`; `__re_run__` node increments `re_run_count` before re-entering generate
