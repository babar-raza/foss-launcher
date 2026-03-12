---
id: TC-3841
title: "Heal Metadata Plumbing — State + WorkerContext + GraphBuilder (H2.3)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, orchestrator, state, worker-context]
depends_on: [TC-3839]
allowed_paths:
  - plans/taskcards/TC-3841_heal_metadata_plumbing.md
  - src/launcher/orchestrator/state.py
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/orchestrator/graph_builder.py
  - tests/unit/orchestrator/test_heal_metadata.py
evidence_required:
  - reports/TC-3841/evidence.md
---

# Taskcard TC-3841 — Heal Metadata Plumbing (H2.3)

## Objective

Add `heal_metadata: dict` to `PipelineGraphState` (state.py), add a
`heal_metadata` property to `WorkerContext` (worker_contract.py), and
wire the pass-through in `_make_worker_node()` (graph_builder.py) so
that heal directives flow from the heal CLI into every worker.

## Required spec references

- `specs/heal.md` (heal directive contract)

## Scope

### In scope
- `PipelineGraphState` TypedDict: add `heal_metadata: dict[str, Any]` field
- `WorkerContext.__init__`: accept optional `heal_metadata: dict | None = None`
- `WorkerContext.heal_metadata` property: returns `dict`
- `_make_worker_node()` in graph_builder.py: inject `heal_metadata` from state into `WorkerContext`
- `_build_resume_state()` in run_loop.py: initialize `heal_metadata: {}` in returned state

### Out of scope
- Workers *using* heal_metadata — TC-3848, TC-3849, TC-3850 (Tier 2)
- Heal CLI setting heal_metadata — TC-3851 (Tier 3)

## Inputs

- `src/launcher/orchestrator/state.py` (41 lines, PipelineGraphState TypedDict)
- `src/launcher/orchestrator/worker_contract.py` (198 lines, WorkerContext)
- `src/launcher/orchestrator/graph_builder.py` (TC-3839 must be Done first)

## Outputs

- `state.py` with `heal_metadata: dict[str, Any]` field
- `worker_contract.py` with `heal_metadata` constructor arg and property
- `graph_builder.py` with heal_metadata injected into WorkerContext
- `run_loop.py` `_build_resume_state()` returning `heal_metadata: {}`

## Allowed paths

- plans/taskcards/TC-3841_heal_metadata_plumbing.md
- src/launcher/orchestrator/state.py
- src/launcher/orchestrator/worker_contract.py
- src/launcher/orchestrator/graph_builder.py
- tests/unit/orchestrator/test_heal_metadata.py

### Allowed paths rationale

Three orchestrator files + new test file. graph_builder.py is already touched by
TC-3839 (which must be Done first per serialization constraint).

## Implementation steps

### Step 1: Add `heal_metadata` to PipelineGraphState (state.py)

Append after `errors: list[str]`:
```python
# -- heal directives (set by heal CLI, read by workers) -------------------
heal_metadata: dict[str, Any]  # empty dict when not in heal mode
```

### Step 2: Add `heal_metadata` to WorkerContext (worker_contract.py)

In `__init__` signature, add parameter:
```python
heal_metadata: dict[str, Any] | None = None,
```

Add instance variable in `__init__` body:
```python
self._heal_metadata: dict[str, Any] = heal_metadata or {}
```

Add property after `telemetry_trace_id` property:
```python
@property
def heal_metadata(self) -> dict[str, Any]:
    """Heal directives injected by the heal CLI (empty dict in normal runs)."""
    return self._heal_metadata
```

### Step 3: Inject heal_metadata in graph_builder.py `_make_worker_node()`

In `_node()` where `WorkerContext` is constructed, pass `heal_metadata`:
```python
ctx = WorkerContext(
    run_id=state["run_id"],
    run_dir=run_dir,
    config=run_config,
    schemas_dir=schemas_dir_path,
    telemetry_client=telemetry_client,
    telemetry_trace_id=telemetry_trace_id,
    heal_metadata=state.get("heal_metadata", {}),
)
```

### Step 4: Initialize heal_metadata in run_loop.py `_build_resume_state()`

Add `heal_metadata: {}` to the returned `PipelineGraphState`:
```python
return PipelineGraphState(
    ...
    errors=[],
    heal_metadata={},
)
```

Also update `execute_run()` initial state construction similarly (search for
`PipelineGraphState(` in run_loop.py and add `heal_metadata={}`).

### Step 5: Add tests

`tests/unit/orchestrator/test_heal_metadata.py`:
- Test: `WorkerContext(heal_metadata={"re_run_count": 1}).heal_metadata == {"re_run_count": 1}`
- Test: `WorkerContext().heal_metadata == {}` (default empty)
- Test: `PipelineGraphState` can be constructed with `heal_metadata={}`
- Test: `_build_resume_state()` returns state with `heal_metadata: {}`

## Failure modes

### Failure mode 1: `state.get("heal_metadata", {})` fails because TypedDict doesn't have field

**Detection**: `KeyError` on `state["heal_metadata"]`
**Resolution**: Use `state.get("heal_metadata", {})` (dict `.get()`) which works even if field
is absent in a partially-initialized state. TypedDict does not enforce at runtime.
**Gate**: Unit test with state dict missing heal_metadata key

### Failure mode 2: `heal_metadata` added to PipelineGraphState breaks LangGraph serialization

**Detection**: LangGraph checkpointer errors if it encounters a non-JSON-serializable value
**Resolution**: `heal_metadata` is typed as `dict[str, Any]` — all values must be JSON primitives.
Document this constraint in code comment: "Must contain only JSON-serializable primitives."
**Gate**: Integration test (TC-3852)

### Failure mode 3: Existing `execute_run()` calls omit `heal_metadata`

**Detection**: `TypeError: PipelineGraphState() missing argument 'heal_metadata'`
**Resolution**: TypedDict fields are not enforced at runtime — use `heal_metadata={}` default
when constructing initial state. Search all `PipelineGraphState(` calls in run_loop.py.
**Gate**: Full regression test

## Task-specific review checklist

1. [ ] `heal_metadata: dict[str, Any]` added to `PipelineGraphState` with doc comment
2. [ ] `WorkerContext.__init__` accepts `heal_metadata: dict | None = None` with default `{}`
3. [ ] `WorkerContext.heal_metadata` property returns `self._heal_metadata`
4. [ ] `_make_worker_node()` passes `state.get("heal_metadata", {})` to WorkerContext
5. [ ] `_build_resume_state()` and `execute_run()` initial state include `heal_metadata: {}`
6. [ ] All existing orchestrator tests still pass (heal_metadata defaults to {} so no behavior change)

## Deliverables

1. `src/launcher/orchestrator/state.py` — `heal_metadata: dict[str, Any]` field
2. `src/launcher/orchestrator/worker_contract.py` — `heal_metadata` constructor arg + property
3. `src/launcher/orchestrator/graph_builder.py` — inject into WorkerContext
4. `tests/unit/orchestrator/test_heal_metadata.py` — 4+ test cases

## Acceptance checks

1. [ ] `pytest tests/unit/orchestrator/test_heal_metadata.py -v` — all PASS
2. [ ] `WorkerContext(heal_metadata={"x": 1}).heal_metadata == {"x": 1}`
3. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [x] Tests: 9/9 PASS (targeted) + 2463/2463 PASS (full suite)
- [x] Validation: heal_metadata flows from state → WorkerContext, verified by test_complex_heal_metadata_preserved
- [x] Evidence file: `reports/TC-3841/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_heal_metadata.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All heal_metadata tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: Heal CLI (TC-3851) sets `heal_metadata` in initial PipelineGraphState
**Downstream**: Workers TC-3848/3849/3850 read `context.heal_metadata` to apply directives
**Contract**: `context.heal_metadata` is always a dict (never None); empty in normal runs
