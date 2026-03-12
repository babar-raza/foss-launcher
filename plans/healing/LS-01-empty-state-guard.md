---
id: LS-01
title: "Add empty-state guard to StreamEventHandler.consume()"
status: Done
priority: Critical
owner: senior-engineer
updated: "2026-03-11"
tags: [streaming, orchestrator, robustness, regression]
depends_on: []
allowed_paths:
  - plans/healing/LS-01-empty-state-guard.md
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/orchestrator/test_stream_progress.py
evidence_required:
  - reports/LS-01/evidence.md
---

# Taskcard LS-01 — Add empty-state guard to StreamEventHandler.consume()

## Gap linkage

Fixes: **LS-G1** (Critical — silent empty-state regression)

## Objective

`StreamEventHandler.consume()` currently returns `{}` if the LangGraph graph errors or
is interrupted before emitting its `LangGraph` `on_chain_end` event. The callers in
`execute_run` then silently produce a `RunResult(report=None, worker_outputs={})` with
no error surfaced. Before TC-4064 the `ainvoke` path would propagate the exception
directly. This taskcard restores the exception-propagation contract by adding a guard
that raises `RuntimeError` when the stream ends without a final state.

## Role

Senior engineer. Drop-in, production-ready.

## Required spec references

- `specs/system_contract.md` (Section: orchestrator error contract — workers must not swallow graph errors)
- `specs/state_events_checkpoints.md` (Section: final state requirements)

## Scope

### Fix
- Add a post-loop guard in `StreamEventHandler.consume()`: after `async for` completes,
  if `self._final_state` is still `{}`, raise `RuntimeError` with a diagnostic message.
- Add a regression test: `test_consume_raises_on_missing_final_state` that feeds an
  async iterator that never emits the `LangGraph` `on_chain_end` event and asserts
  `RuntimeError` is raised.

### Allowed paths
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Forbidden
Any other file or path. In particular: do NOT touch `graph_builder.py`, `state.py`,
`worker_contract.py`, or any worker file.

## Inputs

- `src/launcher/orchestrator/run_loop.py` (current `StreamEventHandler.consume()`)
- `tests/unit/orchestrator/test_stream_progress.py` (current test file)

## Outputs

- `src/launcher/orchestrator/run_loop.py` with guard added
- `tests/unit/orchestrator/test_stream_progress.py` with regression test added

## Allowed paths (frontmatter echo)

- `plans/healing/LS-01-empty-state-guard.md`
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Allowed paths rationale
- `run_loop.py` — contains `StreamEventHandler.consume()` which needs the guard
- `test_stream_progress.py` — existing home for `StreamEventHandler` unit tests

## Implementation steps

### Step 1: Locate the end of `consume()` in `run_loop.py`

Find the `async def consume(self, event_iter)` method in `StreamEventHandler`.
Identify the line after the `async for event in event_iter:` block closes.

### Step 2: Add the empty-state guard

Immediately after the `async for` loop (before the `return self._final_state` line),
insert:

```python
if not self._final_state:
    raise RuntimeError(
        "LangGraph stream completed without emitting a final state. "
        "The graph may have raised an exception or been interrupted before the "
        "'LangGraph' on_chain_end event. Check the run error log for details."
    )
```

The `return self._final_state` line stays as-is after the guard.

### Step 3: Add the regression test in `test_stream_progress.py`

Add a new `@pytest.mark.asyncio` test:

```python
@pytest.mark.asyncio
async def test_consume_raises_on_missing_final_state() -> None:
    """consume() must raise RuntimeError if graph never emits final state."""

    async def _incomplete_stream():
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_chain_start", "name": "evaluate", "data": {}}
        # Deliberately omit the LangGraph on_chain_end event

    handler = StreamEventHandler()
    with pytest.raises(RuntimeError, match="without emitting a final state"):
        await handler.consume(_incomplete_stream())
```

### Step 4: Verify existing tests still pass

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py -v
```

All pre-existing tests must remain green. The new test must pass.

### Step 5: Run the full orchestrator suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short
```

No regressions.

## Failure modes

### Failure mode 1: Guard fires on a valid, short-circuit graph path

**Detection**: A test (or integration run) that intentionally exits the graph early
(e.g., a "dry-run" or "plan-only" mode that emits no `on_chain_end`) now raises.
**Resolution**: Inspect whether the early-exit path is supposed to return a non-empty
state. If so, confirm the `LangGraph` wrapper emits `on_chain_end` for that path too.
If the path genuinely never produces a final state, emit a sentinel `{"_empty": True}`
state from the graph and handle that case in the caller rather than in `consume()`.
**Gate**: `specs/system_contract.md` — orchestrator must propagate errors, not suppress them.

### Failure mode 2: `RuntimeError` message does not match `pytest.raises(match=...)` pattern

**Detection**: New regression test fails with `DID NOT RAISE` or `match` failure.
**Resolution**: Verify the exact string in the `raise RuntimeError(...)` statement
matches the `match=` regex in the test. The substring `"without emitting a final state"`
must appear verbatim.
**Gate**: Test suite green.

### Failure mode 3: Guard added in wrong location (before loop rather than after)

**Detection**: All runs raise `RuntimeError` immediately because `_final_state` is `{}`
before any events are processed.
**Resolution**: Confirm the guard is placed *after* the `async for event in event_iter:`
block closes, not inside it or before it. Use `grep -n "if not self._final_state"` to
verify line placement relative to the `async for` loop.
**Gate**: `test_stream_always_active_returns_correct_state` still passes.

## Task-specific review checklist

1. [ ] Guard is placed after the `async for` loop, not inside or before it
2. [ ] `return self._final_state` is still the last statement in `consume()` (guard uses `raise`, not `return`)
3. [ ] Error message includes actionable text ("Check the run error log") so operators know where to look
4. [ ] New test uses a generator that emits at least one event (not an empty iterator — that's a different scenario)
5. [ ] New test is `async` and decorated with `@pytest.mark.asyncio`
6. [ ] Pre-existing `test_stream_always_active_returns_correct_state` still passes (guard must not fire on valid runs)
7. [ ] Docstrings updated for `consume()` to document the new `RuntimeError` case
8. [ ] Spec file reviewed — no spec drift introduced (behavior change is error propagation, not logic change)
9. [ ] Schema `"description"` fields: not applicable (no schema changes)
10. [ ] `docs/README.md` ownership map checked — no trigger event for this fix
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated (N/A here)

## Deliverables

1. `src/launcher/orchestrator/run_loop.py` — updated `consume()` with guard + updated docstring
2. `tests/unit/orchestrator/test_stream_progress.py` — new `test_consume_raises_on_missing_final_state` test
3. `reports/LS-01/evidence.md` — test run output showing new test passes + all pre-existing orchestrator tests pass

## Acceptance checks

1. [ ] `test_consume_raises_on_missing_final_state` passes
2. [ ] All pre-existing tests in `tests/unit/orchestrator/test_stream_progress.py` still pass
3. [ ] Full orchestrator suite (`tests/unit/orchestrator/`) passes with `PYTHONHASHSEED=0`
4. [ ] `consume()` docstring documents `Raises: RuntimeError` clause
5. [ ] No mock data in production paths (guard uses no mocks)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: orchestrator suite PASS
- [ ] Evidence captured: `reports/LS-01/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py -v
# Expected: all tests pass including test_consume_raises_on_missing_final_state

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short
# Expected: no regressions vs pre-LS-01 baseline
```

**Expected results**:
- `test_consume_raises_on_missing_final_state` PASS
- All other `test_stream_progress.py` tests PASS
- Full orchestrator suite: no new failures

## Integration boundary proven

**Upstream**: LangGraph `astream_events` iterator provided by `execute_run()`
**Downstream**: `execute_run()` receives `final_state` dict and constructs `RunResult`
**Contract**: `consume()` either returns a non-empty `dict[str, Any]` representing the
final pipeline state, or raises `RuntimeError` — it NEVER returns `{}` silently.

## Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | Guard covers all empty-state paths; test covers missing `on_chain_end`; docstring documents the new raise |
| Consistency | Guard behavior matches the pre-TC-4064 `ainvoke` exception-propagation contract |
| Production grading | No silent data-loss path; error message is operator-actionable |
| Systematic approach | Read file → add guard → add test → run orchestrator suite → capture evidence |
| Correctness & spec alignment | Matches `specs/system_contract.md` error propagation requirements |
| Scope & constraints adherence | Only two files touched; no other paths modified |
| Maintainability | One guard, 4 lines; future engineers will see the `RuntimeError` doc and understand the contract |
| Testability | New test is direct, fast, async, no LangGraph process required |
| Robustness | Eliminates the critical silent-failure regression |
| Performance | Zero overhead on happy path (guard only runs after loop completes) |
| Integration fit | Does not change public signature of `consume()` |
| Observability | Error message includes diagnostic text for operators |
| Minimality | 4-line guard + one test; no unnecessary changes |

## Now (runbook)

```bash
# 1. Read the current consume() implementation
grep -n "async def consume" src/launcher/orchestrator/run_loop.py

# 2. Read the surrounding ~30 lines to find exact placement
# (use Read tool lines around the consume method)

# 3. Apply the guard (Edit tool: add 5 lines after async for closes)

# 4. Add the regression test (Edit tool: append to test_stream_progress.py)

# 5. Verify
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py -v

# 6. Run full orchestrator suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short

# 7. Capture evidence
mkdir -p reports/LS-01
# Paste test output into reports/LS-01/evidence.md
```
