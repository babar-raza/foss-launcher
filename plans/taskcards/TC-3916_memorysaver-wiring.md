---
id: TC-3916
title: "Wire LangGraph MemorySaver checkpointer into the pipeline"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [orchestrator, langgraph, checkpointing]
depends_on: [TC-3915]
allowed_paths:
  - plans/taskcards/TC-3916_memorysaver-wiring.md
  - src/launcher/orchestrator/graph_builder.py
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/orchestrator/test_langgraph_checkpointer.py
evidence_required:
  - reports/TC-3916/evidence.md
---

# Taskcard TC-3916 — Wire LangGraph MemorySaver checkpointer into the pipeline

## Objective

Add optional LangGraph MemorySaver checkpointer support to `build_pipeline()` and `execute_run()` so the pipeline graph can persist and resume from LangGraph-native checkpoints, enabling interrupt-based approval flows (TC-3917) and future distributed resumption.

## Required spec references

- `specs/orchestrator.md` (Section: Graph builder and pipeline execution)
- `specs/resilience.md` (Section: Checkpoint and resume policy)

## Scope

### In scope
- Add `checkpointer` and `interrupt_before` params to `build_pipeline()`
- Pass them through to `graph.compile()`
- Add `use_langgraph_checkpoint`, `interrupt_before_publish`, `checkpointer_instance`, `resume_langgraph_thread` params to `execute_run()`
- Add `pending_approval` and `langgraph_thread_id` fields to `RunResult`
- Guard `resume_langgraph_thread` without `checkpointer_instance`
- Unit tests for new params

### Out of scope
- Persistent (disk-backed) checkpointer — only MemorySaver in-process
- UI for approval workflow — covered by TC-3917
- Changes to any worker implementation

## Inputs

- `src/launcher/orchestrator/graph_builder.py` — existing `build_pipeline()`
- `src/launcher/orchestrator/run_loop.py` — existing `execute_run()` and `RunResult`

## Outputs

- Modified `graph_builder.py` with checkpointer/interrupt_before params
- Modified `run_loop.py` with new execute_run params and RunResult fields
- `tests/unit/orchestrator/test_langgraph_checkpointer.py`

## Allowed paths

- plans/taskcards/TC-3916_memorysaver-wiring.md
- src/launcher/orchestrator/graph_builder.py
- src/launcher/orchestrator/run_loop.py
- tests/unit/orchestrator/test_langgraph_checkpointer.py

### Allowed paths rationale
- graph_builder.py: core change point for checkpointer wiring at compile time
- run_loop.py: public API for pipeline execution, holds RunResult dataclass
- test file: required evidence of correctness

## Implementation steps

### Step 1: Add params to build_pipeline()

Add `checkpointer: Any | None = None` and `interrupt_before: list[str] | None = None` to `build_pipeline()` signature. Pass to `graph.compile()`.

### Step 2: Extend RunResult dataclass

Add `pending_approval: bool = False` and `langgraph_thread_id: str = ""` fields.

### Step 3: Add params to execute_run()

Add `use_langgraph_checkpoint`, `interrupt_before_publish`, `checkpointer_instance`, `resume_langgraph_thread` after existing `stream_progress`.

### Step 4: Add guard for resume without checkpointer

Raise ValueError if `resume_langgraph_thread` is set but `checkpointer_instance` is None.

### Step 5: Wire checkpointer setup before build_pipeline call

Create `_checkpointer`, `_interrupt_before`, `_lg_config` locals and pass to `build_pipeline()` and `_stream_execute()`.

### Step 6: Write tests

Create `tests/unit/orchestrator/test_langgraph_checkpointer.py` with three tests verifying the new params.

## Failure modes

### Failure mode 1: MemorySaver import unavailable

**Detection**: `ImportError: cannot import name 'MemorySaver' from 'langgraph.checkpoint.memory'`
**Resolution**: Verify langgraph version with `.venv/Scripts/python.exe -c "import langgraph"`. The import is done lazily inside the function, so it only fails at runtime if `use_langgraph_checkpoint=True`.
**Gate**: Unit test `test_build_pipeline_accepts_checkpointer`

### Failure mode 2: Thread config not passed to astream_events

**Detection**: LangGraph raises `ValueError: thread_id required` when resuming
**Resolution**: Ensure `_lg_config` is populated when `_checkpointer` is set, and `lg_config` is passed (not `{}`) to `_stream_execute`.
**Gate**: Integration test with actual resume

### Failure mode 3: resume_langgraph_thread validation bypassed

**Detection**: `execute_run()` silently ignores `resume_langgraph_thread` without raising
**Resolution**: Ensure the guard is placed AFTER `resume_from` validation but BEFORE run directory creation
**Gate**: `test_resume_without_checkpointer_raises` in TC-3917 test file

## Task-specific review checklist

1. [ ] `build_pipeline()` signature has `checkpointer` and `interrupt_before` params with correct defaults (None)
2. [ ] `graph.compile(interrupt_before=interrupt_before or [])` — empty list, not None
3. [ ] `RunResult` has `pending_approval: bool = False` and `langgraph_thread_id: str = ""`
4. [ ] `execute_run()` has all four new params after `stream_progress`
5. [ ] Guard for `resume_langgraph_thread` without `checkpointer_instance` raises `ValueError`
6. [ ] `_lg_config` is `{"configurable": {"thread_id": run_id}}` when checkpointer is set
7. [ ] `_stream_execute()` call uses `lg_config=_lg_config` (not `lg_config={}`)
8. [ ] TC-3915 `stream_progress` param is not removed or broken
9. [ ] Docstrings updated for `build_pipeline()` and `execute_run()`
10. [ ] Spec file updated if worker behavior changed (confirmed: no spec drift — pure infrastructure)
11. [ ] Schema `"description"` fields present for all new/changed properties (N/A — no schema changes)

## Deliverables

1. Modified `src/launcher/orchestrator/graph_builder.py`
2. Modified `src/launcher/orchestrator/run_loop.py`
3. `tests/unit/orchestrator/test_langgraph_checkpointer.py`

## Acceptance checks

1. [ ] `test_build_pipeline_accepts_checkpointer` passes
2. [ ] `test_build_pipeline_default_no_checkpointer` passes
3. [ ] `test_interrupt_before_param_accepted` passes
4. [ ] Full test suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`

## Self-review

### Verification results
- [ ] Tests: 3/3 PASS
- [ ] Validation: signature inspection PASS
- [ ] Evidence captured: test output

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_langgraph_checkpointer.py -v
```

**Expected results**:
- All 3 tests pass
- No import errors for langgraph.checkpoint.memory

## Integration boundary proven

**Upstream**: `execute_run()` caller (CLI or test) — provides `checkpointer_instance` and flags
**Downstream**: `build_pipeline()` → `graph.compile()` — receives checkpointer and interrupt_before
**Contract**: `graph.compile(checkpointer=..., interrupt_before=[...])` — LangGraph public API
