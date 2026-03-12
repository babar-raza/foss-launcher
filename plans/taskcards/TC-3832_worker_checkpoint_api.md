---
id: TC-3832
title: "worker_checkpoint_api"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [resilience, checkpoint, heal]
depends_on: [TC-3829]
allowed_paths:
  - src/launcher/resilience/checkpoint.py
  - src/launcher/resilience/__init__.py
  - plans/taskcards/TC-3832_worker_checkpoint_api.md
evidence_required:
  - reports/TC-3832/evidence.md
---

# Taskcard TC-3832 — worker_checkpoint_api

## Objective

Add `WorkerCheckpoint` dataclass and three functions (`write_worker_checkpoint`,
`load_worker_checkpoint`, `restore_worker_checkpoint`) to the resilience module
so the heal worker can snapshot and verify per-worker artifacts using SHA-256
content hashes.

## Required spec references

- `specs/11_state_and_events.md` (state recovery, checkpoint semantics)

## Scope

### In scope
- `WorkerCheckpoint` dataclass in `checkpoint.py`
- `write_worker_checkpoint` — writes JSON checkpoint file to `worker_checkpoints/`
- `load_worker_checkpoint` — loads checkpoint by ID, returns None if missing
- `restore_worker_checkpoint` — verifies SHA-256 hash, returns bool
- Export from `resilience/__init__.py`

### Out of scope
- Modifying or removing existing `Checkpoint` / `create_checkpoint` / `list_checkpoints`
- Heal worker that calls these functions (separate TC)

## Inputs

- `src/launcher/resilience/checkpoint.py` (existing file)
- `src/launcher/resilience/__init__.py` (existing file)

## Outputs

- Extended `checkpoint.py` with 1 dataclass + 3 functions
- Updated `__init__.py` exports

## Allowed paths

- src/launcher/resilience/checkpoint.py
- src/launcher/resilience/__init__.py
- plans/taskcards/TC-3832_worker_checkpoint_api.md

### Allowed paths rationale

`checkpoint.py` is the canonical resilience checkpoint module. `__init__.py`
must be updated to re-export new public symbols. Taskcard satisfies AG-002.

## Implementation steps

### Step 1: Add imports and WorkerCheckpoint

Add `import dataclasses` and `import hashlib` to checkpoint.py imports, then
define `WorkerCheckpoint` dataclass before the existing `Checkpoint` dataclass.

### Step 2: Add three functions

Add `write_worker_checkpoint`, `load_worker_checkpoint`, and
`restore_worker_checkpoint` after the `WorkerCheckpoint` dataclass definition.

### Step 3: Update __init__.py

Add `WorkerCheckpoint`, `write_worker_checkpoint`, `load_worker_checkpoint`,
`restore_worker_checkpoint` to both the import list and `__all__`.

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -5
```

### Step 5: Smoke test

```bash
.venv/Scripts/python.exe -c "from launcher.resilience.checkpoint import WorkerCheckpoint, write_worker_checkpoint, load_worker_checkpoint, restore_worker_checkpoint; print('OK')"
```

## Failure modes

### Failure mode 1: `dataclasses.asdict` not available

**Detection**: `AttributeError: module 'dataclasses' has no attribute 'asdict'` at runtime
**Resolution**: `import dataclasses` is added to the top of `checkpoint.py`; use `dataclasses.asdict(cp)`
**Gate**: Python import

### Failure mode 2: `Path.is_relative_to` not available (Python < 3.9)

**Detection**: `AttributeError: 'PosixPath' object has no attribute 'is_relative_to'`
**Resolution**: The venv uses Python 3.10+; `is_relative_to` is available
**Gate**: Unit tests

### Failure mode 3: Worker checkpoint file collision (same-second writes)

**Detection**: Two checkpoints for the same worker in the same second overwrite each other
**Resolution**: The `checkpoint_id` includes microseconds (`%f`), ensuring uniqueness
**Gate**: Integration test

## Task-specific review checklist

1. [x] `WorkerCheckpoint` dataclass has all 6 fields: `checkpoint_id`, `worker`, `run_id`, `created_at`, `artifact_path`, `content_hash`
2. [x] `write_worker_checkpoint` writes to `run_dir/worker_checkpoints/<checkpoint_id>.json`
3. [x] `load_worker_checkpoint` returns `None` (not raises) when file not found
4. [x] `restore_worker_checkpoint` returns `False` (not raises) when artifact not found
5. [x] `__init__.py` exports all 4 new symbols in both import block and `__all__`
6. [x] All existing exports preserved in `__init__.py`

## Deliverables

1. Extended `src/launcher/resilience/checkpoint.py`
2. Updated `src/launcher/resilience/__init__.py`
3. This taskcard at `plans/taskcards/TC-3832_worker_checkpoint_api.md`

## Acceptance checks

1. [x] `from launcher.resilience.checkpoint import WorkerCheckpoint, write_worker_checkpoint, load_worker_checkpoint, restore_worker_checkpoint` succeeds
2. [x] `pytest tests/ -x -q` passes
3. [x] No existing resilience exports removed

## Self-review

### Verification results
- [x] Tests: 2392/2392 PASS (PYTHONHASHSEED=0, run 2026-03-08)
- [x] Checkpoint tests: 22/22 PASS (`tests/unit/resilience/test_checkpoint.py`)
- [x] WorkerCheckpoint fields verified: `checkpoint_id`, `worker`, `run_id`, `created_at`, `artifact_path`, `content_hash`
- [x] Evidence file: `reports/TC-3832/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
22 passed in 0.47s (checkpoint targeted suite)
2392 passed in 53.28s (full suite)
```

Import verification:
```
WorkerCheckpoint fields: ['checkpoint_id', 'worker', 'run_id', 'created_at', 'artifact_path', 'content_hash']
write_worker_checkpoint: <function write_worker_checkpoint at 0x...>
load_worker_checkpoint: <function load_worker_checkpoint at 0x...>
restore_worker_checkpoint: <function restore_worker_checkpoint at 0x...>
```

## Integration boundary proven

**Upstream**: Heal worker calls `write_worker_checkpoint` after each worker re-run
**Downstream**: Heal worker calls `restore_worker_checkpoint` before consuming artifact to detect edits
**Contract**: `WorkerCheckpoint.content_hash` is SHA-256 hex digest of artifact bytes; `restore_worker_checkpoint` returns `True` iff artifact is byte-for-byte identical to when checkpoint was written
