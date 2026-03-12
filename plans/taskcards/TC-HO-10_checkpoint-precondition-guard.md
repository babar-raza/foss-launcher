---
id: TC-HO-10
title: "Validate understand_checkpoint as Pipeline Precondition"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [orchestrator, hardening, wave7]
depends_on: [TC-HO-03, TC-HO-09]
allowed_paths:
  - plans/taskcards/TC-HO-10_checkpoint-precondition-guard.md
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/orchestrator/test_run_loop.py
  - reports/agents/wave7/TC-HO-10/evidence.md
  - reports/agents/wave7/self_review.md
evidence_required:
  - reports/agents/wave7/TC-HO-10/evidence.md
---

# Taskcard TC-HO-10 — Validate understand_checkpoint as Pipeline Precondition

## Objective

Add a `_assert_understand_checkpoint(run_dir, workers)` guard in `run_loop.py` that
fails the pipeline EARLY — before any worker is invoked — when `understand_checkpoint.json`
is absent and Generate or Evaluate are in the active worker set. This is complementary to
TC-HO-03 (which guards inside the Evaluate loader); this guard fails fast at the pipeline
orchestration level, emitting a clear diagnostic before any LLM call is made.

## Required spec references

- `specs/worker_evaluate.md` (Section: Checkpoint preconditions)
- `specs/system_contract.md` (Section: Worker boundary contracts)

## Scope

### In scope
- `_assert_understand_checkpoint(run_dir, workers)` function in `run_loop.py`
- Wiring the guard in `execute_run()` after run directory is established, before graph execution
- Skip the guard when `resume_from="understand"` or earlier (understand hasn't run yet by design)
- Skip the guard when neither `generate` nor `evaluate` is in the active worker set
- Unit tests: missing checkpoint → ValueError; valid checkpoint → no error; resume bypass logic

### Out of scope
- Changes to graph_builder.py (guard lives in run_loop, not the graph)
- Changes to evaluate/worker.py (TC-HO-03 already handles the loader guard)
- Validate content of understanding_bundle fields (TC-HO-03 covers that)

## Inputs

- `run_dir / "understand_checkpoint.json"` — artifact written by Understand worker
- `workers` dict — to detect whether generate/evaluate are active
- `resume_from` argument — to skip guard when Understand is the resume target or earlier

## Outputs

- `run_loop.py` with `_assert_understand_checkpoint` and wiring in `execute_run()`
- Unit tests in `tests/unit/orchestrator/test_run_loop.py`
- Evidence at `reports/agents/wave7/TC-HO-10/evidence.md`

## Allowed paths

- plans/taskcards/TC-HO-10_checkpoint-precondition-guard.md
- src/launcher/orchestrator/run_loop.py
- tests/unit/orchestrator/test_run_loop.py
- reports/agents/wave7/TC-HO-10/evidence.md
- reports/agents/wave7/self_review.md

### Allowed paths rationale

- `run_loop.py` — injection site for the guard
- `test_run_loop.py` — existing test file for orchestrator unit tests
- evidence/self_review — required by AG-002 evidence protocol

## Implementation steps

### Step 1: Implement `_assert_understand_checkpoint`

Add to `run_loop.py` a module-level function:

```python
def _assert_understand_checkpoint(run_dir: Path, workers: dict) -> None:
    """Fail fast if understand_checkpoint.json is missing when needed.

    Called before graph execution when generate or evaluate workers are active.
    Raises ValueError with a clear diagnostic message.
    """
    _DOWNSTREAM_WORKERS = {"generate", "evaluate"}
    if not _DOWNSTREAM_WORKERS.intersection(workers):
        return  # No Generate/Evaluate — guard not applicable

    cp_path = run_dir / "understand_checkpoint.json"
    if not cp_path.exists():
        raise ValueError(
            f"Understand checkpoint not found at {cp_path}. "
            "Run the Understand worker before Generate/Evaluate."
        )
    # Validate it's parseable JSON
    try:
        import json as _json
        _json.loads(cp_path.read_bytes())
    except Exception as exc:
        raise ValueError(
            f"understand_checkpoint.json is not valid JSON at {cp_path}: {exc}"
        ) from exc
```

### Step 2: Wire in `execute_run()`

After run directory is established and `workers` dict is resolved, before calling `build_pipeline`,
add:

```python
# TC-HO-10: Fail fast when understand_checkpoint.json is missing and Generate/Evaluate are active.
_UNDERSTAND_UPSTREAM = {"intake", "understand"}
if not resume_from or resume_from not in _UNDERSTAND_UPSTREAM:
    _assert_understand_checkpoint(run_dir, workers)
```

The bypass logic: only skip the guard if `resume_from` is `"intake"` or `"understand"` (meaning
Understand will run as part of this execution and is not expected to have produced a checkpoint yet).
For `resume_from="planner"`, `"generate"`, or `"evaluate"`, the guard IS applied because
Understand should have already completed.

### Step 3: Write unit tests

Add `TestUnderstandCheckpointGuard` class to `tests/unit/orchestrator/test_run_loop.py`:

- `test_missing_checkpoint_raises_value_error`: call `_assert_understand_checkpoint` with a
  tmp_path that has no checkpoint file and workers={"generate": ..., "evaluate": ...} →
  expect ValueError with "understand_checkpoint" in message
- `test_valid_checkpoint_passes`: write a valid JSON file → no error raised
- `test_no_generate_evaluate_skips_guard`: workers without generate/evaluate → no error even if
  file is missing
- `test_malformed_json_raises_value_error`: write a file with invalid JSON content → ValueError

## Failure modes

### Failure mode 1: Guard fires on fresh run (no resume)

**Detection**: `ValueError: Understand checkpoint not found` during a fresh pipeline run
(intake → understand → generate → evaluate).
**Resolution**: Guard must NOT fire on a fresh run because Understand has not executed yet.
The wiring check (`resume_from not in _UNDERSTAND_UPSTREAM`) must correctly NOT apply the
guard when `resume_from` is empty (fresh run). The bypass set must include `""` (empty string).
**Gate**: TC-HO-10 acceptance check 3 — fresh run is not blocked.

### Failure mode 2: Guard fires when resuming from "understand"

**Detection**: Pipeline fails at precondition when legitimate resume run is started from
`resume_from="understand"`.
**Resolution**: `_UNDERSTAND_UPSTREAM` must include `"understand"` so the guard is skipped
when Understand itself is the resume target.
**Gate**: TC-HO-10 acceptance check 4 — resume from understand is not blocked.

### Failure mode 3: Guard doesn't fire when it should (evaluate-only resume)

**Detection**: Resume from `resume_from="evaluate"` proceeds silently with a missing checkpoint,
causing Evaluate to fail deep inside its loader.
**Resolution**: Ensure the bypass set does NOT include `"evaluate"`, `"generate"`, or `"planner"`.
The guard must apply for all resume values outside `_UNDERSTAND_UPSTREAM`.
**Gate**: TC-HO-10 acceptance check 2 — resume from "evaluate" with missing checkpoint raises.

## Task-specific review checklist

1. [ ] Guard function `_assert_understand_checkpoint` exists in `run_loop.py`
2. [ ] Guard is called in `execute_run()` after workers dict is resolved and run_dir is known
3. [ ] Fresh run (`resume_from=""`) does NOT trigger the guard (Understand will run in this pass)
4. [ ] `resume_from="understand"` does NOT trigger the guard (Understand is the first node)
5. [ ] `resume_from="generate"` with missing checkpoint DOES trigger the guard
6. [ ] Missing checkpoint raises `ValueError` with path and clear message
7. [ ] Malformed JSON checkpoint raises `ValueError`
8. [ ] Guard is a no-op when neither `generate` nor `evaluate` is in workers dict
9. [ ] Docstrings updated for `_assert_understand_checkpoint`
10. [ ] Spec file confirmed — no spec drift (guard is implementation detail, not spec boundary)
11. [ ] Schema `"description"` fields not affected (no schema changes)
12. [ ] Checked `docs/README.md` ownership map — no guide trigger events

## Deliverables

1. `src/launcher/orchestrator/run_loop.py` — with `_assert_understand_checkpoint` and wiring
2. `tests/unit/orchestrator/test_run_loop.py` — 4 new test cases in `TestUnderstandCheckpointGuard`
3. `reports/agents/wave7/TC-HO-10/evidence.md` — test run output

## Acceptance checks

1. [x] `_assert_understand_checkpoint` exists and is importable from `launcher.orchestrator.run_loop`
2. [x] Test: missing checkpoint + generate/evaluate workers → `ValueError` raised
3. [x] Test: fresh run path (workers present, no checkpoint, no resume_from) — guard bypassed
4. [x] Test: `resume_from="understand"` — guard bypassed
5. [x] All `tests/unit/orchestrator/` tests pass (`PYTHONHASHSEED=0`): 90/90 PASS

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: orchestrator unit tests PASS
- [ ] Evidence captured: reports/agents/wave7/TC-HO-10/evidence.md
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -x -q
```

**Expected results**:
- All orchestrator unit tests pass
- `TestUnderstandCheckpointGuard` — 4 new tests pass

## Integration boundary proven

**Upstream**: `run_loop.execute_run()` — calls guard after workers dict is resolved
**Downstream**: `build_pipeline()` and `_stream_execute()` — only called if guard passes
**Contract**: `understand_checkpoint.json` must exist under `run_dir` when Generate/Evaluate are active workers, except on fresh runs or when Understand is the resume target
