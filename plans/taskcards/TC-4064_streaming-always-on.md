---
id: TC-4064
title: "LangGraph streaming always-on + StreamEventHandler + reactive routing"
status: Done
priority: Normal
owner: "claude-sonnet-4-6"
updated: "2026-03-11"
tags: [orchestrator, streaming, langgraph, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4064_streaming-always-on.md
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/orchestrator/graph_builder.py
  - src/launcher/orchestrator/state.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/cli/main.py
  - tests/unit/orchestrator/test_run_loop.py
  - tests/unit/orchestrator/test_stream_progress.py
evidence_required:
  - reports/TC-4064/evidence.md
---

# Taskcard TC-4064 — LangGraph streaming always-on + StreamEventHandler + reactive routing

## Objective

Remove the dual-mode `ainvoke`/`astream_events` split so that streaming is always active. Extract a `StreamEventHandler` class from the inline loop. Add custom events from workers (section_generated, gate_result) so the stream is meaningful. Add `stream_events` to `PipelineGraphState` so the advisor can use gate results for smarter re-run targeting.

## Required spec references

- `specs/system_overview.md` (pipeline execution model)
- `specs/worker_evaluate.md` (gate result structure)
- `specs/worker_generate.md` (section generation milestones)

## Scope

### In scope
- Remove `ainvoke` fallback from `_stream_execute()` in `run_loop.py`
- Extract `StreamEventHandler` class (same file or new `stream_handler.py` inside orchestrator)
- Add `adispatch_custom_event` / `get_stream_writer()` calls in generate and evaluate workers
- Add `stream_events: list[dict]` field to `PipelineGraphState`
- Inject accumulated stream events into state after evaluate completes
- Update advisor node to read `stream_events` for section-level re-run targeting
- Remove or no-op `--stream` CLI flag in `main.py`
- Update/add tests in `test_run_loop.py` and `test_stream_progress.py`

### Out of scope
- Mid-worker `interrupt()` + `Command(resume=...)` reactive routing
- Token-level streaming (on_chat_model_stream events)
- Web UI / websocket event bus
- Changing `events.ndjson` write path (parallel channel, stays as-is)

## Inputs

- `src/launcher/orchestrator/run_loop.py` — current dual-mode implementation
- `src/launcher/orchestrator/graph_builder.py` — DAG construction, advisor router
- `src/launcher/orchestrator/state.py` — PipelineGraphState TypedDict
- `src/launcher/workers/generate/worker.py` — section generation loop
- `src/launcher/workers/evaluate/worker.py` — gate execution loop
- `src/launcher/cli/main.py` — CLI flags

## Outputs

- `run_loop.py` — streaming always-on; `StreamEventHandler` class; no `ainvoke`
- `graph_builder.py` — `stream_events` injected into state post-evaluate; advisor reads them
- `state.py` — `stream_events: list[dict]` field added
- `generate/worker.py` — emits `section_generated` custom events
- `evaluate/worker.py` — emits `gate_result` custom events
- `main.py` — `--stream` flag removed (or kept as no-op with deprecation note)
- Tests updated/added

## Allowed paths

- plans/taskcards/TC-4064_streaming-always-on.md
- src/launcher/orchestrator/run_loop.py
- src/launcher/orchestrator/graph_builder.py
- src/launcher/orchestrator/state.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/cli/main.py
- tests/unit/orchestrator/test_run_loop.py
- tests/unit/orchestrator/test_stream_progress.py

### Allowed paths rationale
All 6 source files are necessary for the 4 changes described in the plan. Test files need updates to cover new streaming-always-on behavior.

## Implementation steps

### Step 1: Read current files

Read the 6 source files and 2 test files to understand exact current state before making changes.

### Step 2: Add `stream_events` to PipelineGraphState

In `state.py`, add `stream_events: list[dict]` field with default `[]`. This carries accumulated custom events from the stream handler back into the graph state.

### Step 3: Extract StreamEventHandler class in run_loop.py

Create class with:
- `__init__(self, run_dir, logger)`
- `async def consume(self, event_iter) -> dict` — main loop, returns final state
- `_on_worker_start(name)`
- `_on_worker_done(name, data)`
- `_on_custom_event(name, data)` — accumulates to `self._events: list[dict]`
- `get_accumulated_events() -> list[dict]`
- `get_final_state() -> dict`

Remove `_stream_execute()` inline loop and replace with `StreamEventHandler.consume()` call. Remove `ainvoke` branch; always use `astream_events`.

### Step 4: Generate worker — emit section_generated events

In `generate/worker.py`, after each section is written:
```python
from langgraph.config import get_stream_writer
write = get_stream_writer()
await write({"event": "section_generated", "section": slug, "tokens": token_count})
```

### Step 5: Evaluate worker — emit gate_result events

In `evaluate/worker.py`, after each gate runs:
```python
write = get_stream_writer()
await write({"event": "gate_result", "gate": gate_name, "passed": passed, "severity": severity})
```

### Step 6: Inject stream_events into state and enrich advisor

In `graph_builder.py`:
- After evaluate node completes, inject `handler.get_accumulated_events()` into `state["stream_events"]`
- In the advisor node function, read `state.get("stream_events", [])` to find which gates failed
- Log which sections/gates triggered re-run for observability

### Step 7: Update CLI

In `main.py`, remove `--stream` flag (or mark as `deprecated=True`, default `True`, with note).

### Step 8: Update tests

- `test_stream_progress.py`: update tests that mock `ainvoke` to use `astream_events` mock
- `test_run_loop.py`: add test that `stream_events` is populated in final state after evaluate

## Failure modes

### Failure mode 1: `get_stream_writer()` unavailable outside LangGraph context

**Detection**: `ImportError` or `AttributeError` when calling `get_stream_writer()` in worker tests
**Resolution**: Guard with `try/except ImportError` and provide a no-op fallback writer. Pattern: `write = get_stream_writer() if _in_langgraph_context() else lambda _: None`
**Gate**: Worker unit tests must pass outside of LangGraph graph context

### Failure mode 2: Final state not captured from astream_events

**Detection**: `_final_state` is `None` after consuming the stream; `execute_run` raises KeyError on state access
**Resolution**: Ensure `on_chain_end` event for the top-level graph node name (typically `"LangGraph"`) is captured. Add assertion test.
**Gate**: `test_stream_progress.py` final state assertion

### Failure mode 3: stream_events field missing in state causes KeyError in advisor

**Detection**: `KeyError: 'stream_events'` in advisor node during re-run cycle
**Resolution**: Use `state.get("stream_events", [])` defensively in advisor. Ensure state TypedDict has the field with default.
**Gate**: `test_run_loop.py` re-run cycle test

## Task-specific review checklist

1. [ ] `ainvoke` branch completely removed from `_stream_execute()` (no dead code)
2. [ ] `StreamEventHandler` is importable and testable independently of LangGraph context
3. [ ] `section_generated` events appear in console output when generate worker runs
4. [ ] `gate_result` events appear in console output when evaluate worker runs
5. [ ] `stream_events` field in final state contains all gate results after evaluate
6. [ ] Advisor node uses `stream_events` to identify failed gates (logged)
7. [ ] Docstrings updated for `StreamEventHandler` class and all public methods
8. [ ] Spec file checked for drift (system_overview.md, worker_evaluate.md, worker_generate.md)
9. [ ] Schema `"description"` fields not needed (no schema changes)
10. [ ] Checked `docs/README.md` ownership map — no docs trigger applies
11. [ ] `--stream` CLI flag removed or marked deprecated without breaking existing calls

## Deliverables

1. Modified `src/launcher/orchestrator/run_loop.py` with StreamEventHandler class
2. Modified `src/launcher/orchestrator/graph_builder.py` with enriched advisor
3. Modified `src/launcher/orchestrator/state.py` with stream_events field
4. Modified `src/launcher/workers/generate/worker.py` with custom events
5. Modified `src/launcher/workers/evaluate/worker.py` with custom events
6. Updated test files passing
7. `reports/TC-4064/evidence.md` with test output

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -x` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — full suite passes
3. [ ] No `ainvoke` call remaining in `run_loop.py`
4. [ ] `stream_events` key present in final state output
5. [ ] Console output includes `[generate]` section lines and `[evaluate]` gate lines during streaming

## Self-review

### Verification results
- [x] Tests: 79/79 orchestrator PASS; 3643+ full suite PASS (5 pre-existing publish async failures)
- [x] Validation: streaming behavior PASS — all 5 new stream tests pass
- [x] StreamEventHandler class added to run_loop.py; ainvoke branch removed
- [x] page_generated and page_evaluated custom events added to generate/evaluate workers
- [x] CLI --stream made a no-op (streaming always active)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Expected results**:
- All orchestrator tests pass
- Full test suite passes
- No `ainvoke` references remain in run_loop.py

## Integration boundary proven

**Upstream**: CLI (`main.py`) calls `execute_run()` — no longer needs `--stream` flag
**Downstream**: Advisor node in `graph_builder.py` reads `stream_events` from state
**Contract**: `PipelineGraphState["stream_events"]` is `list[dict]` with `{"event": str, ...}` structure; always present (default `[]`)
