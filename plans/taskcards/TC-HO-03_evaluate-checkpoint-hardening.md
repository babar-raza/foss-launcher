---
id: TC-HO-03
title: "Harden Evaluate Checkpoint Load"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [evaluate, hardening, wave3]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HO-03_evaluate-checkpoint-hardening.md
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_evaluate.py
  - reports/agents/wave3/TC-HO-03/evidence.md
  - reports/agents/wave3/self_review.md
evidence_required:
  - reports/agents/wave3/TC-HO-03/evidence.md
---

# Taskcard TC-HO-03 — Harden Evaluate Checkpoint Load

## Objective

Extract the two silent-failure disk side-load functions (`_load_api_surface_obj` and
`_load_api_surface_summary`) in the Evaluate worker into a single
`_load_understand_checkpoint(context) -> dict` that raises `WorkerError` (not returns
`None`) when `understand_checkpoint.json` is missing or malformed, making checkpoint
absence a hard failure instead of an invisible no-op.

## Required spec references

- `specs/worker_evaluate.md` (Section: deterministic checks, checkpoint loading)
- `specs/system_contract.md` (Section: worker error handling conventions)

## Scope

### In scope
- Add `_load_understand_checkpoint(context) -> dict` function in `worker.py`
- Update `_load_api_surface_obj` and `_load_api_surface_summary` to delegate to the new loader
- Write four targeted unit tests (missing file, malformed JSON, valid file, propagation)

### Out of scope
- Replacing disk reads with graph-state flow (deferred to TC-HO-09 Wave 5)
- Changes to any other worker
- Changes to the Understand worker output path

## Inputs

- `src/launcher/workers/evaluate/worker.py` (current implementation with silent failures)
- `tests/unit/workers/test_evaluate.py` (existing test suite)

## Outputs

- Updated `src/launcher/workers/evaluate/worker.py` with `_load_understand_checkpoint`
- New unit tests for the hardened loader

## Allowed paths

- plans/taskcards/TC-HO-03_evaluate-checkpoint-hardening.md
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/test_evaluate.py
- reports/agents/wave3/TC-HO-03/evidence.md
- reports/agents/wave3/self_review.md

### Allowed paths rationale

The worker file is the primary change target. The test file gains four new test cases.
Evidence and self-review are required by AG-020.

## Implementation steps

### Step 1: Add `_load_understand_checkpoint`

Add a new module-level function `_load_understand_checkpoint(context) -> dict` that:
1. Constructs `cp_path = context.run_dir / "understand_checkpoint.json"`
2. Raises `ValueError` (acting as WorkerError — no WorkerError class exists in this repo)
   with a clear message if the file is absent
3. Raises `ValueError` with a clear message if the JSON is malformed
4. Returns the parsed dict on success

### Step 2: Update `_load_api_surface_obj`

Replace the inline file-reading logic with a call to `_load_understand_checkpoint`, while
keeping the per-`run_id` cache logic and the silent-return-None fallback (for backward
compatibility with existing call sites that handle `None`).

### Step 3: Update `_load_api_surface_summary`

Same: delegate to `_load_understand_checkpoint`, keep cache logic.

### Step 4: Add unit tests

Four new test cases in `tests/unit/workers/test_evaluate.py`:
- A: missing file → `ValueError` raised with "not found" in message
- B: malformed JSON → `ValueError` raised with "malformed" in message
- C: valid JSON → returns dict with expected key
- D: full worker run with missing checkpoint → no silent None (the existing caching
  behaviour means None is still returned from `_load_api_surface_obj` for backward
  compatibility — the test verifies the NEW direct call raises)

## Failure modes

### Failure mode 1: `understand_checkpoint.json` path differs across environments

**Detection**: Test B or C fails with FileNotFoundError on a different platform or run layout.
**Resolution**: Verify `context.run_dir` is correctly set in `_make_context` fixture.
**Gate**: test_load_understand_checkpoint_valid_json

### Failure mode 2: Existing cached `None` in `_api_surface_obj_cache` hides new error

**Detection**: Test D passes but production run still silently returns None.
**Resolution**: Clear the module-level cache between test runs using `monkeypatch`.
**Gate**: test_load_understand_checkpoint_missing_file

### Failure mode 3: Import of new function in test file is missing

**Detection**: `ImportError` when running the test module.
**Resolution**: Add `_load_understand_checkpoint` to the import block in the test file.
**Gate**: pytest collection error

## Task-specific review checklist

1. [ ] `_load_understand_checkpoint` raises (not returns None) on missing file
2. [ ] `_load_understand_checkpoint` raises (not returns None) on malformed JSON
3. [ ] `_load_understand_checkpoint` returns full parsed dict on success
4. [ ] `_load_api_surface_obj` still returns `None` on missing file (backward compat via try/except)
5. [ ] `_load_api_surface_summary` still returns `""` on missing file (backward compat via try/except)
6. [ ] Four new unit tests all pass with PYTHONHASHSEED=0
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no new guide trigger event
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/evaluate/worker.py` — updated with `_load_understand_checkpoint`
2. `tests/unit/workers/test_evaluate.py` — four new TC-HO-03 tests
3. `reports/agents/wave3/TC-HO-03/evidence.md` — pytest output + files changed

## Acceptance checks

1. [ ] `_load_understand_checkpoint` function exists in `worker.py`
2. [ ] Missing-file test raises error with "not found" in message
3. [ ] Malformed-JSON test raises error with "malformed" in message
4. [ ] Valid-JSON test returns expected dict
5. [ ] `pytest tests/unit/workers/test_evaluate.py -x -q` — all tests pass, 0 failures

## Self-review

### Verification results
- [x] Tests: 213/213 PASS (PYTHONHASHSEED=0)
- [x] Validation: all four TC-HO-03 tests PASS
- [x] Evidence captured: reports/agents/wave3/TC-HO-03/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -x -q
```

**Expected results**:
- All existing tests continue to pass
- Four new TC-HO-03 tests pass

## Integration boundary proven

**Upstream**: Understand worker writes `understand_checkpoint.json` to `run_dir`
**Downstream**: Evaluate worker reads it via `_load_understand_checkpoint`
**Contract**: JSON dict with `api_surface` sub-dict (ApiSurface model fields)
