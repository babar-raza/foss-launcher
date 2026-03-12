---
id: TC-3840
title: "Run Loop Resume Path with Worker Checkpoint Validation (H2.2)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, checkpoint, orchestrator, resume]
depends_on: [TC-3839]
allowed_paths:
  - plans/taskcards/TC-3840_run_loop_resume.md
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/orchestrator/test_run_loop.py
evidence_required:
  - reports/TC-3840/evidence.md
---

# Taskcard TC-3840 — Run Loop Resume Path with Worker Checkpoint Validation (H2.2)

## Objective

Augment `run_loop.py`'s `_build_resume_state()` to use `load_worker_checkpoint()`
and verify SHA-256 content hashes when resuming, so that manually-edited artifacts
trigger a warning before the pipeline proceeds.

## Required spec references

- `specs/heal.md` (checkpoint integrity contract)

## Scope

### In scope
- In `_build_resume_state()`, after loading each `{worker}_checkpoint.json`,
  call `load_worker_checkpoint()` to retrieve the WorkerCheckpoint metadata
- Compare stored `content_hash` against current artifact hash (SHA-256)
- Emit `WARNING` log if hash differs (manual edit detected)

### Out of scope
- Blocking pipeline on hash mismatch — warning only
- Heal loop itself — TC-3851
- heal_metadata pass-through — TC-3841 (separate sequential task)

## Inputs

- `src/launcher/orchestrator/run_loop.py` (existing `_build_resume_state()` at line 110)
- `src/launcher/resilience/checkpoint.py` (load_worker_checkpoint from TC-3832)

## Outputs

- `run_loop.py` with SHA-256 integrity check in resume path
- Warning log when artifact was manually edited between runs

## Allowed paths

- plans/taskcards/TC-3840_run_loop_resume.md
- src/launcher/orchestrator/run_loop.py
- tests/unit/orchestrator/test_run_loop.py

### Allowed paths rationale

Only `run_loop.py` needs modification plus its test file.

## Implementation steps

### Step 1: Add import

In `run_loop.py`, add import:
```python
from launcher.resilience.checkpoint import load_worker_checkpoint
```

### Step 2: Augment `_build_resume_state()`

After loading `worker_outputs[wname]` from `store.load_json(checkpoint_name, ...)`:
```python
# Check for manual edits via SHA-256 integrity check
try:
    wcp = load_worker_checkpoint(run_dir, wname)
    if wcp is not None:
        artifact_path = run_dir / checkpoint_name
        if artifact_path.is_file():
            import hashlib
            current_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if current_hash != wcp.content_hash:
                logger.warning(
                    "Checkpoint artifact for '%s' has been manually edited "
                    "(stored hash: %s, current: %s). Resume may produce "
                    "inconsistent results.",
                    wname, wcp.content_hash[:8], current_hash[:8],
                )
except Exception:
    logger.debug("Could not load worker checkpoint for %s; skipping integrity check", wname)
```

### Step 3: Add/update tests

In `tests/unit/orchestrator/test_run_loop.py`, add:
- Test: hash matches → no warning emitted
- Test: hash differs → warning logged
- Test: no WorkerCheckpoint → no crash (graceful skip)

## Failure modes

### Failure mode 1: `load_worker_checkpoint` raises exception

**Detection**: FileNotFoundError or JSON decode error from checkpoint metadata file
**Resolution**: Wrapped in `try/except Exception` with `logger.debug`; resume proceeds normally
**Gate**: Unit test (no WorkerCheckpoint path)

### Failure mode 2: Artifact file missing during hash check

**Detection**: `artifact_path.is_file()` returns False
**Resolution**: `is_file()` guard prevents crash; no hash check performed
**Gate**: Unit test (missing artifact path)

### Failure mode 3: hashlib not imported

**Detection**: `NameError: name 'hashlib' is not defined`
**Resolution**: Add `import hashlib` at the top of `run_loop.py`, not inside the function
**Gate**: Import smoke test

## Task-specific review checklist

1. [ ] `load_worker_checkpoint(run_dir, wname)` called after each checkpoint load in resume loop
2. [ ] Hash mismatch → `logger.warning()` with truncated hashes (first 8 chars)
3. [ ] No exception from missing WorkerCheckpoint crashes the resume path
4. [ ] `hashlib` imported at module level (not inside function)
5. [ ] Existing resume logic (worker_outputs population) unchanged
6. [ ] All existing run_loop tests still pass

## Deliverables

1. `src/launcher/orchestrator/run_loop.py` — SHA-256 integrity check in resume path
2. `tests/unit/orchestrator/test_run_loop.py` — integrity check test cases

## Acceptance checks

1. [ ] `pytest tests/unit/orchestrator/test_run_loop.py -v` — 0 failures
2. [ ] Hash mismatch path emits WARNING (verified via caplog fixture)
3. [ ] `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [x] Tests: 4/4 PASS (targeted) + 2433/2433 PASS (full suite)
- [x] Validation: warning log verified for hash mismatch via caplog in test
- [x] Evidence file: `reports/TC-3840/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_loop.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All run_loop tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: Pipeline run writes WorkerCheckpoint files via TC-3839
**Downstream**: Resume path loads checkpoints with integrity verification
**Contract**: `load_worker_checkpoint(run_dir, worker_name)` → `WorkerCheckpoint | None`
