---
id: LS-02
title: "Move _safe_stream_event to shared orchestrator module"
status: Done
priority: High
owner: senior-engineer
updated: "2026-03-11"
tags: [streaming, maintainability, deduplication, workers]
depends_on: []
allowed_paths:
  - plans/healing/LS-02-safe-stream-event-dedup.md
  - src/launcher/orchestrator/stream_events.py
  - src/launcher/orchestrator/__init__.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/orchestrator/test_stream_progress.py
evidence_required:
  - reports/LS-02/evidence.md
---

# Taskcard LS-02 — Move _safe_stream_event to shared orchestrator module

## Gap linkage

Fixes: **LS-G2** (Significant — `_safe_stream_event` duplicated in two worker files;
will silently diverge as more workers are added)

## Objective

`_safe_stream_event` is copy-pasted verbatim into both `generate/worker.py` and
`evaluate/worker.py`. Any future worker author will copy it again without knowing where
the canonical version lives. This taskcard extracts the helper into
`src/launcher/orchestrator/stream_events.py`, updates both workers to import from there,
exports the symbol from `orchestrator/__init__.py`, and adds a direct unit test for the
no-op behaviour outside a LangGraph context.

## Role

Senior engineer. Drop-in, production-ready.

## Required spec references

- `specs/system_contract.md` (Section: worker contract — workers use `ctx.*` or
  well-known shared modules for orchestrator-level operations)
- `specs/worker_generate.md` (Section: LLM call instrumentation)
- `specs/worker_evaluate.md` (Section: evaluation event emission)

## Scope

### Fix
- Create `src/launcher/orchestrator/stream_events.py` with the canonical
  `safe_stream_event(name, data)` async function (public name, no leading underscore).
- Update `generate/worker.py`: remove local `_safe_stream_event`, import
  `safe_stream_event` from `launcher.orchestrator.stream_events`.
- Update `evaluate/worker.py`: same.
- Export `safe_stream_event` from `src/launcher/orchestrator/__init__.py`.
- Add `test_safe_stream_event_noop_outside_langgraph` to `test_stream_progress.py`.

### Allowed paths
- `src/launcher/orchestrator/stream_events.py` (new file)
- `src/launcher/orchestrator/__init__.py`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/evaluate/worker.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Forbidden
Any other file or path. Do NOT touch `run_loop.py` (that is LS-01's scope),
`state.py`, `graph_builder.py`, or any non-worker file.

## Inputs

- `src/launcher/workers/generate/worker.py` (local `_safe_stream_event` definition)
- `src/launcher/workers/evaluate/worker.py` (local `_safe_stream_event` definition)
- `src/launcher/orchestrator/__init__.py` (current exports)

## Outputs

- `src/launcher/orchestrator/stream_events.py` — new canonical module
- Updated `generate/worker.py` — imports from shared module
- Updated `evaluate/worker.py` — imports from shared module
- Updated `orchestrator/__init__.py` — exports `safe_stream_event`
- Updated test file — adds no-op unit test

## Allowed paths (frontmatter echo)

- `plans/healing/LS-02-safe-stream-event-dedup.md`
- `src/launcher/orchestrator/stream_events.py`
- `src/launcher/orchestrator/__init__.py`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/evaluate/worker.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Allowed paths rationale
- `stream_events.py` — new canonical home for the shared helper
- `orchestrator/__init__.py` — needs re-export so callers can `from launcher.orchestrator import safe_stream_event`
- `generate/worker.py` — currently contains local duplicate; must be updated
- `evaluate/worker.py` — currently contains local duplicate; must be updated
- `test_stream_progress.py` — existing orchestrator test home; add the no-op test here

## Implementation steps

### Step 1: Create `src/launcher/orchestrator/stream_events.py`

```python
"""LangGraph custom event helpers for use in worker nodes.

Workers call ``safe_stream_event`` to emit structured progress events through the
LangGraph streaming protocol.  Outside a LangGraph execution context (e.g. unit
tests that call worker functions directly) the call is a silent no-op so that
test code does not need to mock the LangGraph runtime.
"""
from __future__ import annotations


async def safe_stream_event(name: str, data: dict) -> None:
    """Emit a LangGraph custom stream event; no-op outside graph execution context.

    Args:
        name: Event name (e.g. ``"page_generated"``, ``"page_evaluated"``).
        data: Arbitrary JSON-serialisable payload forwarded to the stream consumer.

    Raises:
        Nothing — all exceptions are suppressed so a broken LangGraph context
        does not crash a worker.
    """
    try:
        from langgraph.config import adispatch_custom_event  # type: ignore[import]
        await adispatch_custom_event(name, data)
    except Exception:  # noqa: BLE001
        pass
```

### Step 2: Update `generate/worker.py`

- Remove the local `async def _safe_stream_event(name, data)` definition (and its
  import of `langgraph.config`).
- Add at the top-level import block:
  ```python
  from launcher.orchestrator.stream_events import safe_stream_event as _safe_stream_event
  ```
  (Keep the `_safe_stream_event` alias so call sites require zero changes.)

### Step 3: Update `evaluate/worker.py`

Same transformation as Step 2.

### Step 4: Export from `orchestrator/__init__.py`

Add to the exports in `src/launcher/orchestrator/__init__.py`:

```python
from .stream_events import safe_stream_event  # noqa: F401
```

### Step 5: Add the no-op unit test to `test_stream_progress.py`

```python
@pytest.mark.asyncio
async def test_safe_stream_event_noop_outside_langgraph() -> None:
    """safe_stream_event must silently no-op when called outside a LangGraph context."""
    from launcher.orchestrator.stream_events import safe_stream_event

    # Should complete without raising even though there is no LangGraph context
    await safe_stream_event("page_generated", {"slug": "test", "words": 100})
```

### Step 6: Verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    tests/unit/workers/test_generate.py \
    tests/unit/workers/test_understand.py \
    -v --tb=short
```

No regressions; new test passes.

### Step 7: Run wider worker suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/ tests/unit/orchestrator/ -v --tb=short
```

## Failure modes

### Failure mode 1: Circular import between `orchestrator` and workers

**Detection**: `ImportError: cannot import name 'safe_stream_event'` when running any
worker test. LangGraph or the orchestrator may already import workers, creating a cycle.
**Resolution**: Move `stream_events.py` to `src/launcher/shared/stream_events.py`
instead (outside the orchestrator package). Update the import path in both workers and
the `__init__.py` export. `src/launcher/shared/` has no reverse dependency on workers.
**Gate**: `python -c "from launcher.workers.generate import worker"` exits 0.

### Failure mode 2: `_safe_stream_event` alias breaks because of name clash

**Detection**: `NameError: name '_safe_stream_event' is not defined` at call sites in
the worker.
**Resolution**: Verify the alias line is `from launcher.orchestrator.stream_events
import safe_stream_event as _safe_stream_event` and that it is placed in the module-level
import block, not inside a function.
**Gate**: Worker tests pass.

### Failure mode 3: `orchestrator/__init__.py` export causes import side-effects

**Detection**: Tests that import only `from launcher.orchestrator import StreamEventHandler`
now also import LangGraph transitively, causing slow or broken test collection.
**Resolution**: The `safe_stream_event` function defers the `langgraph` import inside
the `try` block, so module-level import of `stream_events.py` is cheap. Verify with
`python -c "import launcher.orchestrator; print('ok')"`.
**Gate**: Test collection time does not increase by more than 1 second.

## Task-specific review checklist

1. [ ] Local `_safe_stream_event` definitions fully removed from both worker files (no stubs, no `# deprecated` comments)
2. [ ] Alias import `as _safe_stream_event` preserves all call sites without modification
3. [ ] `stream_events.py` has module docstring explaining the no-op contract for test contexts
4. [ ] `safe_stream_event` exported from `orchestrator/__init__.py`
5. [ ] No circular import: `python -c "from launcher.workers.generate import worker"` exits 0
6. [ ] New unit test verifies no-op outside LangGraph context (no mock required)
7. [ ] Docstrings present for `safe_stream_event` including `Args`, `Raises`
8. [ ] Spec file reviewed — no spec drift (behaviour identical, location changed)
9. [ ] Schema changes: none
10. [ ] `docs/README.md` ownership map checked — no trigger event applies
11. [ ] If a new `docs/guides/` file was added: update `docs/README.md` (N/A here)

## Deliverables

1. `src/launcher/orchestrator/stream_events.py` — new canonical module with full docstrings
2. `src/launcher/workers/generate/worker.py` — local duplicate removed, alias import added
3. `src/launcher/workers/evaluate/worker.py` — local duplicate removed, alias import added
4. `src/launcher/orchestrator/__init__.py` — `safe_stream_event` re-exported
5. `tests/unit/orchestrator/test_stream_progress.py` — `test_safe_stream_event_noop_outside_langgraph` added
6. `reports/LS-02/evidence.md` — test run output

## Acceptance checks

1. [ ] `test_safe_stream_event_noop_outside_langgraph` passes
2. [ ] All pre-existing generate and evaluate worker tests pass
3. [ ] `grep -r "_safe_stream_event\s*=" src/launcher/workers/` returns zero results (no more local definitions)
4. [ ] `from launcher.orchestrator import safe_stream_event` works in a Python REPL
5. [ ] Full orchestrator + worker suite passes with `PYTHONHASHSEED=0`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: worker + orchestrator suite PASS
- [ ] Evidence captured: `reports/LS-02/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean

## E2E verification

```bash
# Check no local definitions remain
grep -rn "async def _safe_stream_event" src/launcher/workers/

# Run targeted suites
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    tests/unit/workers/test_generate.py \
    -v --tb=short

# Run full worker + orchestrator suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/ tests/unit/orchestrator/ \
    -v --tb=short
```

**Expected results**:
- `grep` returns zero matches
- `test_safe_stream_event_noop_outside_langgraph` PASS
- No regressions in worker or orchestrator suites

## Integration boundary proven

**Upstream**: Worker functions (`generate/worker.py`, `evaluate/worker.py`) that call
`_safe_stream_event`
**Downstream**: `StreamEventHandler` in `run_loop.py` that receives custom events via
LangGraph's `on_custom_event` dispatch
**Contract**: `safe_stream_event(name, data)` is a silent no-op outside LangGraph
context; inside context it dispatches a `custom_event` with `event["name"] == name`
and `event["data"] == data`.

## Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All three locations (two workers + `__init__.py`) updated; test covers the no-op contract explicitly |
| Consistency | Alias import preserves all existing call sites unchanged |
| Production grading | No duplicate code; no import side-effects; circular import checked |
| Systematic approach | Read both workers → create module → update imports → verify → evidence |
| Correctness | Behaviour is strictly identical to the removed duplicates |
| Scope adherence | Only 5 files touched; no other paths modified |
| Maintainability | Future workers discover `safe_stream_event` in `orchestrator/__init__.py` or `stream_events.py` naturally |
| Testability | No-op test requires no mocks, runs in milliseconds |
| Robustness | Exception swallowing is now documented and centralised |
| Performance | Deferred `langgraph` import inside `try` keeps module load cheap |
| Integration fit | Export from `orchestrator/__init__.py` matches pattern of other orchestrator symbols |
| Observability | Module docstring explains the LangGraph context requirement |
| Minimality | One new file, 4 import lines changed, one test; no unnecessary refactoring |

## Now (runbook)

```bash
# 1. Read both worker files to see the local definitions
grep -n "_safe_stream_event" src/launcher/workers/generate/worker.py
grep -n "_safe_stream_event" src/launcher/workers/evaluate/worker.py

# 2. Read orchestrator/__init__.py to find the current exports block
grep -n "^from" src/launcher/orchestrator/__init__.py

# 3. Create stream_events.py (Write tool)

# 4. Edit generate/worker.py: remove local def, add alias import (Edit tool)

# 5. Edit evaluate/worker.py: same (Edit tool)

# 6. Edit orchestrator/__init__.py: add re-export (Edit tool)

# 7. Add test (Edit tool on test_stream_progress.py)

# 8. Verify no local defs remain
grep -rn "async def _safe_stream_event" src/launcher/workers/

# 9. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/ tests/unit/orchestrator/ -v --tb=short

# 10. Capture evidence
mkdir -p reports/LS-02
```
