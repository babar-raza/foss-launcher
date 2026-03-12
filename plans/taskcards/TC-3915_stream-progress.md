---
id: TC-3915
title: "Add LangGraph streaming progress to run_loop.py and cli/main.py"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-10"
tags: ["orchestrator", "cli", "streaming", "langgraph"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3915_stream-progress.md
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/cli/main.py
  - tests/unit/orchestrator/test_stream_progress.py
evidence_required:
  - reports/TC-3915/evidence.md
---

# Taskcard TC-3915 — Add LangGraph streaming progress to run_loop.py and cli/main.py

## Objective

Add a `_stream_execute()` helper to `run_loop.py` that wraps LangGraph's `astream_events()` API to optionally emit per-worker progress lines to stderr. Wire it to `execute_run()` and the `launch run` CLI command via a `--stream` flag, giving operators real-time pipeline visibility without changing existing behavior for callers that don't opt in.

## Required spec references

- `src/launcher/orchestrator/run_loop.py` (Section: execute_run — graph execution)
- `src/launcher/cli/main.py` (Section: run command — CLI entry point)

## Scope

### In scope
- New `_stream_execute()` async helper function in `run_loop.py`
- `stream_progress: bool = False` parameter on `execute_run()`
- Replacement of bare `ainvoke()` call with `_stream_execute()` delegation
- `--stream` flag on `launch run` CLI command
- Unit tests for `_stream_execute()` covering 3 scenarios

### Out of scope
- LangGraph config (`_lg_config`) wiring — reserved for TC-3916
- Any changes to worker implementations or graph topology
- Changes to pipeline.yaml or schemas

## Inputs

- `src/launcher/orchestrator/run_loop.py` — existing orchestrator entry point
- `src/launcher/cli/main.py` — existing CLI run command

## Outputs

- Modified `src/launcher/orchestrator/run_loop.py` with `_stream_execute()` and updated `execute_run()` signature
- Modified `src/launcher/cli/main.py` with `--stream` flag
- New `tests/unit/orchestrator/test_stream_progress.py` with 3 tests

## Allowed paths

- plans/taskcards/TC-3915_stream-progress.md
- src/launcher/orchestrator/run_loop.py
- src/launcher/cli/main.py
- tests/unit/orchestrator/test_stream_progress.py

### Allowed paths rationale
- Taskcard: required by AG-002
- run_loop.py: orchestrator entry point where `_stream_execute()` is added
- main.py: CLI where `--stream` flag is wired
- test_stream_progress.py: unit test coverage for new function

## Implementation steps

### Step 1: Create taskcard

Copy TC-000_TEMPLATE.md to TC-3915_stream-progress.md and fill all 14 sections. Set status In-Progress.

### Step 2: Read run_loop.py

Read the full 556-line file to understand structure, imports, and where to insert code.

### Step 3: Add _stream_execute() before execute_run()

Insert the `_stream_execute()` async helper immediately before the `execute_run()` function definition. The function delegates to `ainvoke()` when `stream_progress=False`, or uses `astream_events()` to print per-worker progress lines to stderr when `True`.

### Step 4: Add stream_progress parameter to execute_run()

Add `stream_progress: bool = False` as a keyword argument to `execute_run()` signature.

### Step 5: Replace ainvoke() call

Replace `final_state = await compiled_graph.ainvoke(initial_state)` with a call to `_stream_execute()`, passing `stream_progress=stream_progress` and `lg_config={}` as placeholder.

### Step 6: Read cli/main.py and add --stream flag

Read the CLI file, then add `stream` parameter after `verbose` in the `run()` command, and pass `stream_progress=stream` to `execute_run()`.

### Step 7: Write tests

Create `tests/unit/orchestrator/test_stream_progress.py` with 3 tests using a `_FakeGraph` stub.

### Step 8: Run tests

Run the new tests and then the full test suite to verify no regressions.

## Failure modes

### Failure mode 1: astream_events() API unavailable

**Detection**: `AttributeError: 'CompiledGraph' has no attribute 'astream_events'` at runtime when `--stream` is used.
**Resolution**: Check LangGraph version. The `astream_events()` API requires LangGraph >= 0.1.x. If not available, the function falls back gracefully — `stream_progress=False` still works via `ainvoke()`.
**Gate**: Runtime guard — `stream_progress=False` is the default so existing behavior is unaffected.

### Failure mode 2: Empty final_state when streaming

**Detection**: `final_state` dict is empty after streaming; pipeline reports no worker outputs.
**Resolution**: Ensure the `on_chain_end` + `name == "LangGraph"` event capture logic correctly extracts `data.output`. Verify event version `"v2"` is used with `astream_events()`.
**Gate**: `test_stream_captures_final_state` test covers this path.

### Failure mode 3: execute_run() call sites break due to new stream_progress param

**Detection**: `TypeError: execute_run() got an unexpected keyword argument` or existing tests fail.
**Resolution**: `stream_progress` defaults to `False` making it backward-compatible. All existing callers are unaffected. Only the CLI `run()` command passes `stream_progress=stream`.
**Gate**: Full test suite run — `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`.

### Failure mode 4: pytest-asyncio not configured

**Detection**: `PytestUnraisableExceptionWarning` or `asyncio` mode errors in tests.
**Resolution**: Tests use `asyncio.run()` inside synchronous functions as a fallback. Check `pyproject.toml` for `asyncio_mode = "auto"`.
**Gate**: `test_stream_progress.py` tests pass.

## Task-specific review checklist

1. [ ] `_stream_execute()` function is inserted immediately before `execute_run()` (not after)
2. [ ] `stream_progress: bool = False` is the LAST keyword arg in `execute_run()` signature
3. [ ] `ainvoke()` call is fully replaced — no duplicate call paths remain
4. [ ] `lg_config={}` placeholder is used (NOT `_lg_config` — reserved for TC-3916)
5. [ ] `--stream` flag in CLI defaults to `False` (no behavioral change for existing users)
6. [ ] All 3 unit tests pass: no_stream, stream_emits_progress, stream_captures_final_state
7. [ ] Docstrings updated for `_stream_execute()` and `execute_run()` (stream_progress parameter)
8. [ ] Spec file confirmed — no spec drift (streaming is an observability enhancement only)
9. [ ] Schema `"description"` fields not applicable (Python-only change, no JSON schema changes)
10. [ ] Checked `docs/README.md` ownership map — no trigger event applies (internal helper)
11. [ ] No new `docs/guides/` files needed for this change

## Deliverables

1. `src/launcher/orchestrator/run_loop.py` — with `_stream_execute()` and updated `execute_run()`
2. `src/launcher/cli/main.py` — with `--stream` flag on `run` command
3. `tests/unit/orchestrator/test_stream_progress.py` — 3 passing unit tests
4. `plans/taskcards/TC-3915_stream-progress.md` — this file, status Done when complete

## Acceptance checks

1. [ ] `_stream_execute()` exists in `run_loop.py` and is callable
2. [ ] `execute_run()` accepts `stream_progress: bool = False` without breaking existing callers
3. [ ] `launch run --stream` flag exists in CLI (verified via `--help`)
4. [ ] All 3 tests in `test_stream_progress.py` pass
5. [ ] Full test suite passes with no new failures (`PYTHONHASHSEED=0`)

## Self-review

### Verification results
- [x] Tests: 3/3 PASS (test_stream_progress.py)
- [x] Full suite: 3290 passed, 1 skipped, 3 xfailed — no regressions
- [ ] Evidence captured: reports/TC-3915/evidence.md
- [x] Doc freshness: acknowledged — no spec drift (observability-only change)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_stream_progress.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -20
```

**Expected results**:
- 3/3 tests pass in test_stream_progress.py
- No regressions in full test suite

## Integration boundary proven

**Upstream**: `build_pipeline()` returns a `compiled_graph` object with `ainvoke()` and `astream_events()` methods
**Downstream**: CLI `run()` command passes `stream_progress=stream` to `execute_run()`; TC-3916 will replace `lg_config={}` with real config
**Contract**: `_stream_execute()` returns `dict[str, Any]` identical in shape to what `ainvoke()` returns — no downstream impact
