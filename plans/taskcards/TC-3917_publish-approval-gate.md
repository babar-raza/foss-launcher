---
id: TC-3917
title: "Add publish approval gate (interrupt_before_publish + --require-approval CLI flag)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [orchestrator, cli, approval-gate, langgraph]
depends_on: [TC-3916]
allowed_paths:
  - plans/taskcards/TC-3917_publish-approval-gate.md
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/cli/main.py
  - tests/unit/orchestrator/test_publish_gate.py
evidence_required:
  - reports/TC-3917/evidence.md
---

# Taskcard TC-3917 — Add publish approval gate (interrupt_before_publish + --require-approval CLI flag)

## Objective

Pause the pipeline before the publish worker and require explicit human approval before proceeding, using LangGraph's `interrupt_before` mechanism wired in TC-3916. Adds a `--require-approval` CLI flag and a `_run_with_approval()` helper that serializes the approval flow.

## Required spec references

- `specs/orchestrator.md` (Section: Pipeline execution and approval flows)
- `specs/publish.md` (Section: Publish safety gate)

## Scope

### In scope
- `interrupt_before_publish` logic in `execute_run()`: detect interrupt state, write `pending_approval.json`, return early `RunResult` with `pending_approval=True`
- `--require-approval` flag on `run` CLI command
- `_run_with_approval()` async helper using MemorySaver + two-phase execute_run
- `_print_pre_publish_summary()` helper
- Unit tests for RunResult fields and execute_run signature

### Out of scope
- Persistent approval storage across process restarts (MemorySaver is in-process only)
- Web UI or API endpoint for approval
- Changes to publish worker internals

## Inputs

- `src/launcher/orchestrator/run_loop.py` — `execute_run()` with TC-3916 checkpointer params
- `src/launcher/cli/main.py` — existing `run` command with `stream` flag

## Outputs

- Modified `run_loop.py` with interrupt detection and early return
- Modified `cli/main.py` with `--require-approval`, `_print_pre_publish_summary()`, `_run_with_approval()`
- `tests/unit/orchestrator/test_publish_gate.py`

## Allowed paths

- plans/taskcards/TC-3917_publish-approval-gate.md
- src/launcher/orchestrator/run_loop.py
- src/launcher/cli/main.py
- tests/unit/orchestrator/test_publish_gate.py

### Allowed paths rationale
- run_loop.py: interrupt detection and pending_approval.json write
- main.py: CLI flag and approval helper functions
- test file: unit tests for RunResult and signature checks

## Implementation steps

### Step 1: Add interrupt detection in execute_run()

After `_stream_execute()` call, check `aget_state()` if `interrupt_before_publish` is set. If `"publish"` is in `lg_state.next`, write `pending_approval.json` and return early `RunResult(pending_approval=True, langgraph_thread_id=run_id)`.

### Step 2: Add CLI helpers

Add `_print_pre_publish_summary()` and `_run_with_approval()` functions to `cli/main.py` after `run()`.

### Step 3: Add --require-approval param

Add `require_approval: bool = typer.Option(...)` to `run()` command signature.

### Step 4: Update asyncio.run() call

Conditionally use `_run_with_approval()` if `require_approval` is True, else use existing `execute_run()` call.

### Step 5: Write tests

Create `tests/unit/orchestrator/test_publish_gate.py` with 4 tests verifying RunResult fields and execute_run signature.

## Failure modes

### Failure mode 1: aget_state() returns unexpected structure

**Detection**: `AttributeError: 'NoneType' has no attribute 'next'` or `lg_state.next` is not iterable
**Resolution**: Guard with `(lg_state.next or ())` — empty tuple if None. Already in the implementation.
**Gate**: `test_run_result_has_pending_approval_field`

### Failure mode 2: Approval callback blocks event loop

**Detection**: `asyncio` deadlock or `RuntimeError: This event loop is already running`
**Resolution**: Use `run_in_executor(None, cb)` to run blocking input() in a thread pool. Already implemented in `_run_with_approval()`.
**Gate**: Manual testing with `--require-approval` flag

### Failure mode 3: Resume without thread_id fails

**Detection**: LangGraph raises `ValueError` or silently re-runs entire pipeline
**Resolution**: Pass `resume_langgraph_thread=result.langgraph_thread_id` (the original run_id) in the second `execute_run()` call inside `_run_with_approval()`.
**Gate**: `test_resume_without_checkpointer_raises`

### Failure mode 4: store.write_json path incorrect

**Detection**: `FileNotFoundError` when writing `pending_approval.json`
**Resolution**: `store` variable is `ArtifactStore(run_dir=run_dir)` — already bound. Use `store.write_json("pending_approval.json", {...})`.
**Gate**: Check `store` variable name by reading `execute_run()` body

## Task-specific review checklist

1. [ ] `interrupt_before_publish` detection uses `aget_state()` with correct thread config
2. [ ] `pending_approval.json` written with `run_id`, `pending_node`, `verdict` fields
3. [ ] Early return `RunResult` has `pending_approval=True` and `langgraph_thread_id=run_id`
4. [ ] `_write_final_snapshot()` called before early return (for observability)
5. [ ] `--require-approval` flag appears in `run()` command after `stream` param
6. [ ] `_run_with_approval()` uses same `MemorySaver` instance for both `execute_run()` calls
7. [ ] TC-3915 `--stream` flag is not broken or removed
8. [ ] Docstrings updated for helpers and modified functions
9. [ ] Spec file confirmed: no spec drift (pure CLI/orchestrator infrastructure)
10. [ ] Schema descriptions: N/A — no schema changes
11. [ ] `docs/README.md` ownership map checked — no guide trigger applies

## Deliverables

1. Modified `src/launcher/orchestrator/run_loop.py`
2. Modified `src/launcher/cli/main.py`
3. `tests/unit/orchestrator/test_publish_gate.py`

## Acceptance checks

1. [ ] `test_run_result_has_pending_approval_field` passes
2. [ ] `test_run_result_defaults` passes
3. [ ] `test_execute_run_signature_has_interrupt_params` passes
4. [ ] `test_resume_without_checkpointer_raises` passes
5. [ ] Full test suite: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: 4/4 PASS
- [ ] Validation: signature inspection PASS
- [ ] Evidence captured: test output

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_publish_gate.py -v
```

**Expected results**:
- All 4 tests pass
- `RunResult` has `pending_approval` and `langgraph_thread_id` fields
- `execute_run()` accepts all 4 new params

## Integration boundary proven

**Upstream**: `_run_with_approval()` in CLI — provides MemorySaver instance and interrupt flag
**Downstream**: LangGraph graph execution — uses `interrupt_before=["publish"]` at compile time
**Contract**: `RunResult.pending_approval=True` triggers the approval prompt; second `execute_run()` with same saver resumes from interrupt point
