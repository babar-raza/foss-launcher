# Healing Plan: SR-3869 — Guard Correctness & Test Coverage

**Source**: Self-review of TC-3869 (resume skip guard in `graph_builder.py`)
**Priority**: HIGH — SR-01 is a correctness defect that can silently skip a broken worker

---

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| SR-01 | `None`-valued cache entry triggers skip guard incorrectly | TC-SR-01 |
| SR-02 | Missing test cases: None-value, all-cached, intake-skipped | TC-SR-02 |
| SR-08 | `worker_skipped` event payload missing `re_run_count` field | TC-SR-03 |

---

## TC-SR-01 — Fix None-value guard in resume skip check

**Status**: Done
**Gap linkage**: SR-01
**Role**: Senior engineer. Drop-in, production-ready.

### Context

The current skip guard fires when `worker_name in (state.get("worker_outputs") or {})`. This checks
for key *existence*, not value validity. A `None` value stored at `worker_outputs["understand"]`
(e.g. from a degenerate checkpoint load or a future code path) would still trigger the skip, causing
the worker to be permanently bypassed with no error. The fix narrows the check to `value is not None`.

### Scope

**Fix**:
In `src/launcher/orchestrator/graph_builder.py`, inside `_make_worker_node._node()`, replace the
existing skip guard condition:

```python
# BEFORE
if state.get("re_run_count", 0) == 0 and worker_name in (state.get("worker_outputs") or {}):

# AFTER
_cached_output = (state.get("worker_outputs") or {}).get(worker_name)
if state.get("re_run_count", 0) == 0 and _cached_output is not None:
```

The rest of the block (logger.info, ctx.emit_event, return) is unchanged.

**Allowed paths**:
- `src/launcher/orchestrator/graph_builder.py`
- `tests/unit/orchestrator/test_graph_builder.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py -v` — 0 failures
- **UI/Web/API**: N/A
- **Tests**: The new test `test_none_value_in_worker_outputs_does_not_skip` (added in TC-SR-02) must PASS
- **Config respected end-to-end**: Resume with a valid checkpoint file still skips correctly
- **No mock data in production paths**: guard reads directly from `state["worker_outputs"]`; no mock injection

### Deliverables

1. **`src/launcher/orchestrator/graph_builder.py`** — guard condition updated (2-line change)
2. **`tests/unit/orchestrator/test_graph_builder.py`** — `test_none_value_in_worker_outputs_does_not_skip` test added (covered by TC-SR-02)

### Hard rules

- Keep public signatures: `_make_worker_node` signature unchanged
- No new deps introduced
- Deterministic: guard is a pure dict lookup, no side effects
- Code/docs/tests kept in sync: the comment on the guard must be updated to mention `None` check

### Review dimensions (what "5/5" means here)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Guard fires IFF `value is not None` AND `re_run_count == 0` |
| Robustness | `None`, missing key, and empty dict all handled correctly |
| Testability | Explicit test for `None`-value case, happy-path test unchanged |
| Minimality | 2-line change, no refactoring beyond the guard condition |
| Observability | log message unchanged; event only fires on valid skip |

### Now (runbook)

```bash
# 1. Edit graph_builder.py — replace guard condition (see Scope above)
# 2. Verify the logic:
#    _cached_output = None  →  skip does NOT fire  ✓
#    _cached_output = {}    →  skip DOES fire       ✓  (empty dict is not None)
#    _cached_output = {...} →  skip DOES fire       ✓
# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py::TestResumeSkipCachedWorkers -v
# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## TC-SR-02 — Add missing test cases for resume skip guard

**Status**: Done
**Gap linkage**: SR-02
**Role**: Senior engineer. Drop-in, production-ready.

### Context

The current `TestResumeSkipCachedWorkers` suite (5 tests) covers: skip fires, event emitted,
no-skip on empty cache, no-skip on re-run, partial resume. Three cases are missing:
1. `None` value in `worker_outputs` → worker must NOT be skipped (regression for SR-01 fix)
2. All workers cached → none run (simulates `resume_from="last_worker"` with full cache)
3. `intake` worker skipped — `intake` is `active_workers[0]`, which goes through `__heal_router__`
   routing first, making it a distinct code path from `understand`

### Scope

**Fix**: Add 3 new test methods to `TestResumeSkipCachedWorkers` in `test_graph_builder.py`.

New test 1 — None-value does not skip:
```python
def test_none_value_in_worker_outputs_does_not_skip(self, tmp_path: Path) -> None:
    """A None value stored under a worker key must NOT trigger the skip guard."""
    graph, workers = _build_heal_graph(tmp_path)
    run_config = _make_run_config()
    state = _make_resume_state(
        tmp_path, run_config,
        worker_outputs={"understand": None},
        re_run_count=0,
    )
    asyncio.run(graph.ainvoke(state))
    assert workers["understand"].call_count == 1, (
        "A None cached value must not skip the worker — only non-None outputs are trusted"
    )
```

New test 2 — All workers cached, none run:
```python
def test_all_workers_cached_none_run(self, tmp_path: Path) -> None:
    """When all workers have cached outputs, none of them call worker.run()."""
    graph, workers = _build_heal_graph(tmp_path)
    run_config = _make_run_config()
    state = _make_resume_state(
        tmp_path, run_config,
        worker_outputs={
            "understand": {"status": "cached"},
            "planner": {"status": "cached"},
            "generate": {"status": "cached"},
        },
        re_run_count=0,
    )
    asyncio.run(graph.ainvoke(state))
    assert workers["understand"].call_count == 0, "Understand should be skipped (all cached)"
    assert workers["planner"].call_count == 0, "Planner should be skipped (all cached)"
    assert workers["generate"].call_count == 0, "Generate should be skipped (all cached)"
```

New test 3 — Uses the single-worker "dummy" pipeline with a single-worker graph to test
that the guard works when the skipped worker IS `active_workers[0]`:
```python
_SINGLE_WORKER_PIPELINE_YAML = """\
version: "2.0"
defaults:
  max_re_runs: 0
  schema_dir: "specs/schemas"
pipeline:
  - worker: dummy
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
"""

def test_first_worker_in_pipeline_skipped_when_cached(self, tmp_path: Path) -> None:
    """active_workers[0] is skipped when its output is in worker_outputs.

    This covers the case where the very first node (no __heal_router__) is the skip target.
    """
    import json as _json
    from launcher.orchestrator.graph_builder import build_pipeline

    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text(_SINGLE_WORKER_PIPELINE_YAML, encoding="utf-8")
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(exist_ok=True)
    (schema_dir / "run_config.schema.json").write_text(
        _json.dumps({"type": "object"}), encoding="utf-8"
    )
    dummy_worker = _CallTrackingWorker("dummy")
    graph = build_pipeline(cfg_file, {"dummy": dummy_worker}, schema_dir=schema_dir)

    run_config = _make_run_config()
    state = _make_resume_state(
        tmp_path, run_config,
        worker_outputs={"dummy": {"status": "cached"}},
        re_run_count=0,
    )
    asyncio.run(graph.ainvoke(state))
    assert dummy_worker.call_count == 0, (
        "active_workers[0] must be skipped when its output is already cached"
    )
```

**Allowed paths**:
- `tests/unit/orchestrator/test_graph_builder.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py::TestResumeSkipCachedWorkers -v` — all 8 tests pass (5 existing + 3 new)
- **UI/Web/API**: N/A
- **Tests**: All 3 new tests must pass; must include a failure path (None-value test is the regression)
- **Config respected end-to-end**: Tests use actual `build_pipeline` with temp pipeline YAML
- **No mock data in production paths**: Tests invoke real `graph.ainvoke`; only worker.run is tracking

### Deliverables

1. **`tests/unit/orchestrator/test_graph_builder.py`** — 3 new test methods in `TestResumeSkipCachedWorkers`; `_SINGLE_WORKER_PIPELINE_YAML` constant added at module level (or inside the test class)

### Hard rules

- No network in tests: all tests use `tmp_path`, no HTTP calls
- Deterministic: `asyncio.run` is deterministic for these sync-equivalent workers
- No new deps: only uses existing fixtures and helpers
- Keep existing tests passing

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | 8 tests cover: skip, event, no-skip-empty, no-skip-rerun, partial, None, all-cached, first-worker |
| Correctness | Each test asserts exactly one behavior; assertion messages explain WHY |
| Robustness | Regression test (None-value) prevents silent re-introduction of SR-01 |
| Minimality | 3 new test methods + 1 constant; no new helpers beyond what's needed |
| Maintainability | `_SINGLE_WORKER_PIPELINE_YAML` is self-contained inline; no shared state |

### Now (runbook)

```bash
# 1. Add _SINGLE_WORKER_PIPELINE_YAML constant near _HEAL_PIPELINE_YAML in test file
# 2. Add the 3 test methods to TestResumeSkipCachedWorkers
# 3. Run targeted
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py::TestResumeSkipCachedWorkers -v
# Expected: 8 tests, 0 failures
# 4. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## TC-SR-03 — Add re_run_count to worker_skipped event payload

**Status**: Done
**Gap linkage**: SR-08
**Role**: Senior engineer. Drop-in, production-ready.

### Context

The `worker_skipped` event emitted by the resume skip guard does not include `re_run_count`.
This makes it impossible to correlate skips with the re-run loop state in log analysis or telemetry
dashboards. Adding the field costs nothing and improves debuggability.

### Scope

**Fix**:
In `src/launcher/orchestrator/graph_builder.py`, inside the resume skip guard block:

```python
# BEFORE
ctx.emit_event(
    "worker_skipped",
    {"worker": worker_name, "reason": "resume_checkpoint"},
    worker=worker_name,
)

# AFTER
ctx.emit_event(
    "worker_skipped",
    {
        "worker": worker_name,
        "reason": "resume_checkpoint",
        "re_run_count": state.get("re_run_count", 0),
    },
    worker=worker_name,
)
```

**Allowed paths**:
- `src/launcher/orchestrator/graph_builder.py`
- `tests/unit/orchestrator/test_graph_builder.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py::TestResumeSkipCachedWorkers::test_worker_skipped_event_emitted_for_cached_worker -v` — PASS
- **UI/Web/API**: N/A
- **Tests**: Update `test_worker_skipped_event_emitted_for_cached_worker` to assert `re_run_count` is present in event data
- **Config respected end-to-end**: Event schema is additive; no schema breakage
- **No mock data in production paths**: Event payload is read directly from state

### Deliverables

1. **`src/launcher/orchestrator/graph_builder.py`** — `re_run_count` added to event payload dict
2. **`tests/unit/orchestrator/test_graph_builder.py`** — existing event test updated to assert `re_run_count` in payload

### Hard rules

- Additive change only — do not remove existing `worker` or `reason` keys
- Keep heal bypass event payload consistent (heal bypass uses different reason; no change needed there)
- No new deps

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Observability | `re_run_count` present in every resume skip event; correlatable with re-run loop state |
| Minimality | 1-field addition; test assertion extended by 1 line |
| Correctness | `state.get("re_run_count", 0)` matches the guard condition's own read |
| Maintainability | Future consumers of the event have richer context without breaking existing consumers |

### Now (runbook)

```bash
# 1. Edit graph_builder.py — add re_run_count to event dict (see Scope)
# 2. Edit test — add assertion:
#    assert resume_skipped[0]["data"].get("re_run_count") == 0
# 3. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
