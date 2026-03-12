---
id: TC-4101
title: "Resume path: detect stale/missing files and emit warning"
status: Done
priority: Medium
owner: Agent-B
updated: "2026-03-11"
tags: [understand, resume, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4101_resume_integrity_check.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand.py
  - reports/agents/B/TC-4101/evidence.md
evidence_required:
  - reports/agents/B/TC-4101/evidence.md
---

# Taskcard TC-4101 — Resume path: detect stale/missing files and emit warning

## Objective

When Understand resumes from a checkpoint, it re-reads files from `repo_info.file_index` via `_read_repo_content()`. If any indexed files were deleted or modified between runs, the content is silently stale or absent. This taskcard adds a missing-file count check immediately after `_read_repo_content()` returns on the resume path, emitting a `context.log.warning()` with the count and persisting the count as `stale_files_on_resume` in `scout_inventory.json`.

## Required spec references

- `specs/worker_understand.md` (Section: Resume path — checkpoint re-read behavior)
- `specs/state_events_checkpoints.md` (Section: Resume integrity requirements)

## Scope

### In scope
- `worker.py` lines 88–96 (resume block only): add missing-file count and warning
- Store `stale_files_on_resume` key in the `scout_inventory.json` artifact
- Unit test in `tests/unit/workers/test_understand.py` verifying warning emission and key presence

### Out of scope
- Modifying Scout worker (file discovery logic unchanged)
- Changing resume behavior — this is an observation/warning only, not a hard failure
- Modifying `_read_repo_content()` internals
- Adding retry or re-clone logic on stale detection

## Inputs

- `src/launcher/workers/understand/worker.py` (resume block at lines 88–96)
- `repo_info.file_index` — list/dict of relative file paths indexed at Scout time
- `context.log` — logger available in WorkerContext

## Outputs

- Updated `worker.py` with missing-file count check and warning
- `scout_inventory.json` artifact with `stale_files_on_resume` key added
- New unit test in `test_understand.py`
- `reports/agents/B/TC-4101/evidence.md`

## Allowed paths

- plans/taskcards/TC-4101_resume_integrity_check.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/test_understand.py
- reports/agents/B/TC-4101/evidence.md

### Allowed paths rationale

- `worker.py` contains the resume block where the check must be inserted
- `test_understand.py` is the existing understand worker test module
- `evidence.md` captures the pytest run proving the warning and key are emitted

## Implementation steps

### Step 1: Count missing files after _read_repo_content()

Inside the resume path (the `if not repo_content and repo_info.file_index:` block), immediately after `_read_repo_content()` returns, add:

```python
missing = sum(1 for p in repo_info.file_index if not (Path(repo_dir) / p).exists())
```

`repo_dir` is already a `Path` in the existing code — use it directly.

### Step 2: Emit warning if any files are missing

Add the conditional warning immediately after the count:

```python
if missing > 0:
    context.log.warning(
        "[Understand] Resume: %d/%d indexed files missing from disk — content may be stale",
        missing,
        len(repo_info.file_index),
    )
```

### Step 3: Store stale_files_on_resume in scout_inventory

In the section where `scout_inventory` dict is assembled (before the `write_json("scout_inventory.json", ...)` call), add:

```python
scout_inventory["stale_files_on_resume"] = missing
```

If `missing` is not in scope at that point (i.e., it is only set inside the resume block), initialize `missing = 0` before the resume block and update it inside the block. This ensures the key is always present in `scout_inventory.json` (value 0 on normal runs, >0 on stale resumes).

### Step 4: Write unit test

In `tests/unit/workers/test_understand.py`, add a test using `tmp_path`:
1. Create a mock `repo_info.file_index` with 3 relative paths (`["a.py", "b.py", "c.py"]`)
2. Create only 2 of the 3 files on disk (delete or never create `c.py`)
3. Invoke the resume path logic (or directly test the counting expression)
4. Assert that a warning was emitted containing "1/3 indexed files missing"
5. Assert that the `scout_inventory` dict has `stale_files_on_resume == 1`

## Failure modes

### Failure mode 1: Path join breaks on Windows backslashes

**Detection**: `(repo_dir / p)` raises `TypeError` if `p` contains Windows path separators or is not a str/Path.
**Resolution**: Use `Path(repo_dir) / Path(p)` — this is safe on all platforms. `Path` normalizes separators automatically. `repo_dir` is already a `Path` in existing code.
**Gate**: `specs/system_contract.md` — cross-platform path handling required.

### Failure mode 2: Empty file_index on first run (not a resume)

**Detection**: `stale_files_on_resume` would be computed on a non-resume path.
**Resolution**: The `if not repo_content and repo_info.file_index:` guard already restricts this block to resume paths only. Initialize `missing = 0` before the block — non-resume runs always write `stale_files_on_resume: 0`, which is correct and harmless.
**Gate**: `specs/worker_understand.md` — normal run path must not be affected.

### Failure mode 3: Very large repos (10K+ files) causing slow stat calls

**Detection**: Resume path takes significantly longer than expected (e.g., >5s on a 10K file repo).
**Resolution**: The check is O(N) disk stat calls. On resume paths this is acceptable since the resume is already performing I/O to re-read file contents. The stat calls are much lighter than content reads. No optimization needed.
**Gate**: Operational — resume is an infrequent, user-initiated action.

## Task-specific review checklist

1. [ ] `missing` variable is initialized to 0 BEFORE the resume block so it is always in scope for scout_inventory
2. [ ] The count uses `(Path(repo_dir) / p).exists()` — not string concatenation
3. [ ] Warning message format includes both missing count AND total count (e.g., "1/3 indexed files missing")
4. [ ] `stale_files_on_resume` key is written to scout_inventory.json on ALL runs (0 on normal, >0 on stale resume)
5. [ ] Unit test verifies warning text contains the correct count
6. [ ] Unit test verifies `scout_inventory["stale_files_on_resume"] == 1` for 1-missing scenario
7. [ ] Docstrings updated for any changed functions in `worker.py`
8. [ ] Spec file `specs/worker_understand.md` reviewed — no spec drift introduced
9. [ ] Schema `"description"` fields present for any new properties (scout_inventory is JSON, add description if schema exists)
10. [ ] Checked `docs/README.md` ownership map — observability change does not require guide update
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated (N/A for this TC)

## Deliverables

1. Updated `src/launcher/workers/understand/worker.py` with missing-file count and warning
2. New unit test in `tests/unit/workers/test_understand.py`
3. `reports/agents/B/TC-4101/evidence.md` with pytest output showing warning emission

## Acceptance checks

- [ ] Unit test passes: missing file detected, warning logged with correct count
- [ ] `stale_files_on_resume` key present in `scout_inventory` dict on resume runs
- [ ] `stale_files_on_resume: 0` on normal (non-resume) runs — key always present
- [ ] No regression on the non-resume path
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: resume stale-file warning PASS
- [ ] Evidence captured: `reports/agents/B/TC-4101/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
```

**Expected results**:
- All pre-existing `test_understand.py` tests PASS
- New stale-file warning test PASS: warning emitted, `stale_files_on_resume == 1`
- New normal-run test PASS: `stale_files_on_resume == 0`

## Integration boundary proven

**Upstream**: `_read_repo_content()` returns repo content from indexed files; `repo_info.file_index` is set by Scout worker
**Downstream**: `scout_inventory.json` is consumed by downstream agents and phase_store promoter for observability
**Contract**: `scout_inventory.json` always contains `stale_files_on_resume` (int ≥ 0) — verified by unit test
