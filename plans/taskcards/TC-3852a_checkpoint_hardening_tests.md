---
id: TC-3852a
title: "Checkpoint Hardening Tests (H4.1)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, checkpoint, tests]
depends_on: [TC-3832, TC-3839]
allowed_paths:
  - plans/taskcards/TC-3852a_checkpoint_hardening_tests.md
  - tests/unit/resilience/test_checkpoint.py
  - reports/TC-3852a/evidence.md
evidence_required:
  - reports/TC-3852a/evidence.md
---

# Taskcard TC-3852a — Checkpoint Hardening Tests (H4.1)

## Objective

Extend `tests/unit/resilience/test_checkpoint.py` with tests for the new
`WorkerCheckpoint` API: `write_worker_checkpoint`, `load_worker_checkpoint`,
`restore_worker_checkpoint`, SHA-256 hash verification, edit detection warning,
missing file, and regression rollback scenarios.

## Required spec references

- `specs/11_state_and_events.md` (checkpoint contract)

## Scope

### In scope
- `TestWorkerCheckpoint` class with 7 test cases added to existing file
- write_worker_checkpoint creates JSON, returns WorkerCheckpoint with valid hash
- load_worker_checkpoint returns None for missing ID, correct object for valid ID
- restore_worker_checkpoint returns True when artifact unchanged, False when edited
- restore_worker_checkpoint returns False when artifact is missing
- WorkerCheckpoint fields: checkpoint_id, worker, run_id, content_hash, artifact_path, created_at
- cleanup_old_checkpoints removes worker_checkpoints (existing test extended)

### Out of scope
- Graph builder integration tests (covered by TC-3839)
- Run loop resume tests (covered by TC-3840/TC-3841)

## Inputs

- `src/launcher/resilience/checkpoint.py` (write_worker_checkpoint, load_worker_checkpoint, restore_worker_checkpoint)
- Existing `tests/unit/resilience/test_checkpoint.py` (17 existing tests)

## Outputs

- 7 new tests in `TestWorkerCheckpoint` class
- All 24+ tests pass

## Allowed paths

- plans/taskcards/TC-3852a_checkpoint_hardening_tests.md
- tests/unit/resilience/test_checkpoint.py
- reports/TC-3852a/evidence.md

## Implementation steps

### Step 1: Add TestWorkerCheckpoint to existing test file

Append after existing test classes:
- test_write_creates_file: write_worker_checkpoint → JSON file exists in worker_checkpoints/
- test_write_returns_checkpoint: returned WorkerCheckpoint has non-empty content_hash
- test_write_hash_is_sha256: hash is 64 hex chars (SHA-256)
- test_load_valid: load_worker_checkpoint by ID → same content_hash
- test_load_missing_returns_none: load nonexistent ID → None
- test_restore_intact: restore_worker_checkpoint when file unchanged → True
- test_restore_tampered: restore after file edit → False
- test_restore_missing_file: restore when artifact deleted → False

## Failure modes

### Failure mode 1: WorkerCheckpoint import path wrong
**Resolution**: Import from `launcher.resilience.checkpoint`
**Gate**: test import succeeds

### Failure mode 2: artifact_path is absolute, not relative
**Resolution**: `write_worker_checkpoint` uses relative path when inside run_dir
**Gate**: test verifies `checkpoint.artifact_path` is relative

### Failure mode 3: tmp_path collision between tests
**Resolution**: Each test uses a fresh `tmp_path` fixture (pytest auto-isolates)
**Gate**: All tests pass in parallel run

## Task-specific review checklist

1. [ ] `write_worker_checkpoint` creates file in `run_dir/worker_checkpoints/`
2. [ ] `content_hash` is 64-char SHA-256 hex
3. [ ] `load_worker_checkpoint` returns None for unknown ID
4. [ ] `restore_worker_checkpoint` returns True when artifact unchanged
5. [ ] `restore_worker_checkpoint` returns False when artifact byte-edited
6. [ ] `restore_worker_checkpoint` returns False when artifact deleted
7. [ ] All new + existing tests pass (0 failures)

## Deliverables

1. `tests/unit/resilience/test_checkpoint.py` — 7 new tests in TestWorkerCheckpoint
2. `reports/TC-3852a/evidence.md` — actual test output

## Acceptance checks

1. [ ] `pytest tests/unit/resilience/test_checkpoint.py -v` — all PASS
2. [ ] `restore_worker_checkpoint` returns False after edit
3. [ ] `pytest tests/ -q` — 0 failures

## Self-review

### Verification results
- [ ] Tests: PASS
- [ ] Evidence file: `reports/TC-3852a/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/resilience/test_checkpoint.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Integration boundary proven

**Upstream**: `write_worker_checkpoint` from TC-3832
**Downstream**: `run_loop.py` resume path uses `restore_worker_checkpoint` for edit detection
**Contract**: `WorkerCheckpoint.content_hash` = SHA-256 of artifact bytes
