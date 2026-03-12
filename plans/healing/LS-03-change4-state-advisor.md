---
id: LS-03
title: "Implement TC-4064 Change 4: stream_events state field + advisor enrichment"
status: Done
priority: High
owner: senior-engineer
updated: "2026-03-11"
tags: [streaming, state, advisor, graph, plan-contract]
depends_on: [LS-02]
allowed_paths:
  - plans/healing/LS-03-change4-state-advisor.md
  - src/launcher/state/__init__.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/orchestrator/__init__.py
  - tests/unit/orchestrator/test_stream_progress.py
  - tests/unit/orchestrator/test_run_loop.py
evidence_required:
  - reports/LS-03/evidence.md
---

# Taskcard LS-03 — Implement TC-4064 Change 4: stream_events state field + advisor enrichment

## Gap linkage

Fixes: **LS-G3** (Significant — Change 4 from TC-4064 approved plan silently dropped:
`state.py` `stream_events` field and `graph_builder.py` advisor enrichment not implemented)

## Objective

The TC-4064 approved plan included Change 4: add a `stream_events: list[dict]` field to
`PipelineGraphState` so that custom events emitted during `generate` and `evaluate` phases
are available to the heal advisor for reactive, page-level re-run decisions. This was
silently dropped. This taskcard implements that change minimally:

1. Add `stream_events: list[dict]` to `PipelineGraphState` in `state/__init__.py`.
2. Have `StreamEventHandler.consume()` populate the field from accumulated custom events
   before returning the final state, so the advisor can read per-page outcomes without
   a separate query.

**Scope limit**: The advisor's *use* of `stream_events` (routing logic changes) is out
of scope for this taskcard. We only make the data available; advisor enrichment that
consumes it is a follow-on task.

## Role

Senior engineer. Drop-in, production-ready.

## Required spec references

- `specs/state_events_checkpoints.md` (Section: PipelineGraphState fields)
- `specs/system_contract.md` (Section: orchestrator/advisor contract)
- `specs/worker_evaluate.md` (Section: per-page evaluation events)

## Scope

### Fix
- Add `stream_events: list[dict]` (default `field(default_factory=list)`) to
  `PipelineGraphState` in `src/launcher/state/__init__.py`.
- In `StreamEventHandler`, accumulate custom events in `self._custom_events: list[dict]`.
  Populate `on_custom_event` to append `{"name": name, "data": data, "ts": timestamp}`.
- In `consume()`, after `_final_state` is populated, merge custom events into the state:
  `self._final_state.setdefault("stream_events", []).extend(self._custom_events)`.
- Add targeted tests covering: (a) custom events appear in final state, (b) field is
  present even when no custom events are emitted (empty list).

### Allowed paths
- `src/launcher/state/__init__.py`
- `src/launcher/orchestrator/run_loop.py`
- `src/launcher/orchestrator/__init__.py`
- `tests/unit/orchestrator/test_stream_progress.py`
- `tests/unit/orchestrator/test_run_loop.py` (if exists; create if needed)

### Forbidden
- `src/launcher/orchestrator/graph_builder.py` — advisor routing logic changes are
  out of scope for this taskcard
- Any worker file — workers already emit events via `safe_stream_event` (LS-02)
- Any schema file — `stream_events` is an internal state field, not a public schema

## Inputs

- `src/launcher/state/__init__.py` (current `PipelineGraphState` definition)
- `src/launcher/orchestrator/run_loop.py` (current `StreamEventHandler`)

## Outputs

- Updated `state/__init__.py` with `stream_events` field
- Updated `run_loop.py` with event accumulation and state merge
- Tests covering the new field

## Allowed paths (frontmatter echo)

- `plans/healing/LS-03-change4-state-advisor.md`
- `src/launcher/state/__init__.py`
- `src/launcher/orchestrator/run_loop.py`
- `src/launcher/orchestrator/__init__.py`
- `tests/unit/orchestrator/test_stream_progress.py`
- `tests/unit/orchestrator/test_run_loop.py`

### Allowed paths rationale
- `state/__init__.py` — contains `PipelineGraphState`; must add `stream_events` field
- `run_loop.py` — contains `StreamEventHandler`; must accumulate and merge events
- `orchestrator/__init__.py` — may need updated exports if `PipelineGraphState` is
  re-exported from there
- `test_stream_progress.py` — primary test file for `StreamEventHandler` behaviour
- `test_run_loop.py` — integration-level orchestrator tests

## Implementation steps

### Step 1: Read `state/__init__.py`

Locate `PipelineGraphState` (likely a `TypedDict` or dataclass). Identify the last field
to know where to append.

### Step 2: Add `stream_events` field to `PipelineGraphState`

If `PipelineGraphState` is a `TypedDict`:
```python
stream_events: list[dict]  # custom events emitted during generate/evaluate phases
```

If it is a dataclass with `field(default_factory=...)`:
```python
stream_events: list[dict] = field(default_factory=list)
```

### Step 3: Add `_custom_events` accumulator to `StreamEventHandler.__init__`

```python
def __init__(self) -> None:
    ...  # existing fields
    self._custom_events: list[dict] = []
```

### Step 4: Accumulate in `_on_custom_event`

Find the `_on_custom_event` method. Append each dispatched event with a timestamp:

```python
import time as _time

def _on_custom_event(self, event: dict) -> None:
    name = event.get("name", "")
    data = event.get("data", {})
    self._custom_events.append({
        "name": name,
        "data": data,
        "ts": _time.monotonic(),
    })
    # ... rest of existing dispatch logic unchanged ...
```

### Step 5: Merge into final state in `consume()`

After the empty-state guard (LS-01), before `return self._final_state`:

```python
# Merge accumulated custom events into final state for advisor/downstream use
if self._custom_events:
    self._final_state.setdefault("stream_events", []).extend(self._custom_events)
```

### Step 6: Add tests

In `test_stream_progress.py`:

```python
@pytest.mark.asyncio
async def test_custom_events_accumulated_in_final_state() -> None:
    """Custom events emitted during graph execution appear in final state stream_events."""

    async def _events_with_custom():
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {
            "event": "on_custom_event",
            "name": "page_generated",
            "data": {"slug": "install", "words": 450},
        }
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"worker_outputs": {"generate": {}}}},
        }

    handler = StreamEventHandler()
    state = await handler.consume(_events_with_custom())
    events = state.get("stream_events", [])
    assert len(events) == 1
    assert events[0]["name"] == "page_generated"
    assert events[0]["data"]["slug"] == "install"


@pytest.mark.asyncio
async def test_stream_events_empty_list_when_no_custom_events() -> None:
    """stream_events key is absent (or empty) when no custom events were emitted."""

    async def _events_no_custom():
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"worker_outputs": {}}},
        }

    handler = StreamEventHandler()
    state = await handler.consume(_events_no_custom())
    # Either key absent or empty list — both are acceptable
    assert state.get("stream_events", []) == []
```

### Step 7: Verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short
```

## Failure modes

### Failure mode 1: `PipelineGraphState` is a `TypedDict` with no default value mechanism

**Detection**: `TypeError: TypedDict does not support default values` at import time.
**Resolution**: For `TypedDict`, the field is declared without a default. Any code that
constructs `PipelineGraphState(...)` without `stream_events` will fail. Find all
construction sites with `grep -rn "PipelineGraphState("` and add `stream_events=[]` to
each, OR use `total=False` for optional fields if the TypedDict allows it.
**Gate**: `python -c "from launcher.state import PipelineGraphState"` exits 0.

### Failure mode 2: LangGraph's `on_chain_end` event format differs from expected

**Detection**: `state.get("stream_events")` is `None` even after running a graph with
custom events, because `_on_custom_event` is never called.
**Resolution**: Log `event["event"]` for all events in `consume()` (behind a debug flag)
and verify the actual event types. LangGraph v0.2+ emits `on_custom_event` for
`adispatch_custom_event` calls; earlier versions may use a different key.
**Gate**: `test_custom_events_accumulated_in_final_state` passes.

### Failure mode 3: Merge step fires after empty-state guard and mutates the wrong dict

**Detection**: `test_stream_always_active_returns_correct_state` fails because
`stream_events` key is missing from a run that had custom events, or is present when it
should be absent.
**Resolution**: Verify that the merge step reads from `self._custom_events` (instance
variable populated during `async for`) not from a local variable. Ensure
`setdefault("stream_events", []).extend(...)` only runs when `self._custom_events` is
non-empty.
**Gate**: Both new tests pass simultaneously.

## Task-specific review checklist

1. [ ] `PipelineGraphState` field added without breaking existing construction sites
2. [ ] `_custom_events` accumulator initialized in `__init__` (not as a class variable)
3. [ ] Merge step in `consume()` is after the LS-01 empty-state guard (ordering matters)
4. [ ] `ts` field uses `time.monotonic()` (not wall clock — avoids flaky time-dependent tests)
5. [ ] Test `test_custom_events_accumulated_in_final_state` does not depend on LangGraph runtime
6. [ ] Test `test_stream_events_empty_list_when_no_custom_events` asserts the absent/empty contract
7. [ ] Docstring on `stream_events` field explains its purpose (advisor input)
8. [ ] Spec file `specs/state_events_checkpoints.md` reviewed for drift
9. [ ] Schema changes: none (stream_events is internal state, not a public schema boundary)
10. [ ] `docs/README.md` ownership map checked — no trigger event applies
11. [ ] `StreamEventHandler` docstring updated to mention event accumulation

## Deliverables

1. `src/launcher/state/__init__.py` — `stream_events` field added
2. `src/launcher/orchestrator/run_loop.py` — `_custom_events` accumulator + merge in `consume()`
3. `tests/unit/orchestrator/test_stream_progress.py` — two new tests
4. `reports/LS-03/evidence.md` — test run output

## Acceptance checks

1. [ ] `test_custom_events_accumulated_in_final_state` passes
2. [ ] `test_stream_events_empty_list_when_no_custom_events` passes
3. [ ] All pre-existing orchestrator tests pass
4. [ ] `PipelineGraphState` importable with `stream_events` field present
5. [ ] `grep -n "stream_events" src/launcher/state/__init__.py` shows the field declaration

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: orchestrator suite PASS
- [ ] Evidence captured: `reports/LS-03/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean

## E2E verification

```bash
# Verify state field exists
python -c "from launcher.state import PipelineGraphState; print('stream_events' in PipelineGraphState.__annotations__)"

# Run orchestrator suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short

# Specifically verify new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    -k "custom_events or stream_events" -v
```

**Expected results**:
- State field check prints `True`
- Two new tests PASS
- No regressions in orchestrator suite

## Integration boundary proven

**Upstream**: `safe_stream_event` calls in `generate/worker.py` and `evaluate/worker.py`
(dispatched via LangGraph) which populate `StreamEventHandler._on_custom_event`
**Downstream**: Heal advisor in `graph_builder.py` (future LS-03 follow-on) reads
`state["stream_events"]` to make page-level re-run decisions
**Contract**: `final_state["stream_events"]` is a `list[dict]` where each entry has
`{"name": str, "data": dict, "ts": float}`. Empty list when no events emitted.

## Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | State field + accumulator + merge + two tests; no aspect of Change 4 left pending within this scope |
| Consistency | Merge step placed after LS-01 empty-state guard; state field matches TC-4064 approved plan spec |
| Production grading | No mutation of the original `_final_state` dict until after loop completes; `setdefault` is safe for both empty and non-empty cases |
| Systematic approach | Read state module → add field → read run_loop → add accumulator + merge → add tests → verify |
| Correctness | `stream_events` is populated exactly from `_on_custom_event` dispatch (no double-counting) |
| Scope adherence | Advisor routing logic deferred; only state + StreamEventHandler touched |
| Maintainability | `_custom_events` is an instance variable (not class-level), so concurrent `StreamEventHandler` instances are isolated |
| Testability | Tests require no LangGraph runtime — purely synthetic async iterators |
| Robustness | `setdefault(...).extend(...)` is safe whether or not `_final_state` already has a `stream_events` key |
| Performance | One list append per custom event; merge is O(n) with n = events emitted |
| Integration fit | Field name matches TC-4064 approved plan verbatim |
| Observability | `ts` field allows post-hoc performance analysis of which pages are slow |
| Minimality | ~10 lines added to `run_loop.py`, 1 field in `state.py`, 2 tests; no unnecessary abstractions |

## Now (runbook)

```bash
# 1. Read state/__init__.py to find PipelineGraphState
grep -n "class PipelineGraphState\|stream_events" src/launcher/state/__init__.py

# 2. Read StreamEventHandler in run_loop.py
grep -n "class StreamEventHandler\|_custom_events\|_on_custom_event\|def consume" \
    src/launcher/orchestrator/run_loop.py

# 3. Add field to PipelineGraphState (Edit tool)

# 4. Add _custom_events: list[dict] = [] to __init__ (Edit tool)

# 5. Append to _on_custom_event (Edit tool)

# 6. Add merge step in consume() after empty-state guard (Edit tool)

# 7. Add two tests (Edit tool on test_stream_progress.py)

# 8. Run orchestrator suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/ -v --tb=short

# 9. Capture evidence
mkdir -p reports/LS-03
```
