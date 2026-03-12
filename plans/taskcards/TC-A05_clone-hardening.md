---
id: TC-A05
title: "Harden clone failure behavior"
status: In-Progress
priority: Normal
owner: "agent-b1"
updated: "2026-03-11"
tags: [intake, clone, hardening, resilience]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-A05_clone-hardening.md
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/intake/clone.py
  - reports/TC-A05/evidence.md
evidence_required:
  - reports/TC-A05/evidence.md
---

# Taskcard TC-A05 — Harden clone failure behavior

## Objective

Improve failure diagnostics for clone operations by (1) distinguishing network failures from empty remote responses in `check_remote_sha()`, and (2) detecting empty/unreadable repo_dir in `self_review()` to catch corrupt clones early.

## Required spec references

- `specs/worker_understand.md` (Section: clone acquisition)
- `specs/system_contract.md` (Section: resilience)

## Scope

### In scope
- `check_remote_sha()` returns `None` on network failure vs `""` for no HEAD line
- `clone_repo_cached()` fallback block logs "network failure" vs "empty SHA" based on `remote_sha is None`
- `IntakeWorker.self_review()` detects empty repo_dir and unreadable repo_dir

### Out of scope
- Retry logic for clone operations (belongs in resilience layer)
- Changes to IntakeBundle model
- Changes to RunConfig validation

## Inputs

- `clone.py` — `check_remote_sha()` and `clone_repo_cached()` functions
- `worker.py` — `IntakeWorker.self_review()` method

## Outputs

- `clone.py` — `check_remote_sha()` returns `str | None`
- `worker.py` — `self_review()` checks for empty/unreadable repo_dir

## Allowed paths

- plans/taskcards/TC-A05_clone-hardening.md
- src/launcher/workers/intake/worker.py
- src/launcher/workers/intake/clone.py
- reports/TC-A05/evidence.md

### Allowed paths rationale

`clone.py` — where `check_remote_sha()` return type is updated. `worker.py` — where `self_review()` gets the empty-dir check. `evidence.md` — captures test results as proof.

## Implementation steps

### Step 1: Update check_remote_sha() return type

Change `check_remote_sha()` to return `str | None`:
- Return `None` when a subprocess exception is caught (network/permission failure)
- Return `""` when ls-remote succeeds but no HEAD line is present
- Update docstring and log message for the `None` path

### Step 2: Update clone_repo_cached() fallback logging

In the `if not remote_sha and cache_dir.exists() and marker.exists():` block,
differentiate between `remote_sha is None` (network failure) and `remote_sha == ""` (empty response).

### Step 3: Add empty/unreadable repo_dir check to self_review()

After the existing `if output.repo_dir and not Path(output.repo_dir).is_dir():` check, add:
- If repo_dir exists but has no entries → finding: corrupt clone
- If repo_dir exists but PermissionError on iterdir → finding: permission denied

### Step 4: Run tests

`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v`

### Step 5: Capture evidence

Write test results to `reports/TC-A05/evidence.md`.

## Failure modes

### Failure mode 1: check_remote_sha returns None breaks caller

**Detection**: TypeError in `clone_repo_cached` where `not remote_sha` logic fails.
**Resolution**: `not None` evaluates to `True` in Python — same behavior as `not ""`. No change needed in caller.
**Gate**: Unit tests for clone with network failure scenario.

### Failure mode 2: Empty dir check raises unexpected exception

**Detection**: `PermissionError` not caught, propagates from `self_review()`.
**Resolution**: Wrap `Path.iterdir()` in `try/except PermissionError` as specified.
**Gate**: self_review unit test with unreadable dir mock.

### Failure mode 3: Marker file missing for empty SHA path

**Detection**: `marker.exists()` is False when `remote_sha` is `""` — no cache used, fresh clone attempted.
**Resolution**: Expected behavior — fallback only triggers when marker exists.
**Gate**: clone_repo_cached unit test with empty remote_sha.

## Task-specific review checklist

1. [x] `check_remote_sha()` returns `None` on exception, `""` on empty response
2. [x] Fallback log message distinguishes `None` vs `""` remote_sha
3. [x] `self_review()` checks `any(Path(repo_dir).iterdir())` for empty dir
4. [x] `PermissionError` caught separately in `self_review()`
5. [x] No existing caller behavior changed — `not remote_sha` catches both `None` and `""`
6. [x] Docstring updated on `check_remote_sha()`
7. [x] Docstrings updated for all new/changed public functions
8. [x] Spec file confirmed — no new spec drift introduced
9. [x] Schema fields not affected
10. [x] `docs/README.md` ownership map checked — no trigger event
11. [x] No new `docs/guides/` file added

## Deliverables

1. Modified `src/launcher/workers/intake/clone.py` with `check_remote_sha()` returning `str | None`
2. Modified `src/launcher/workers/intake/worker.py` with empty/unreadable dir detection in `self_review()`
3. `reports/TC-A05/evidence.md` with test results

## Acceptance checks

1. [ ] `tests/unit/workers/test_intake.py` all pass with PYTHONHASHSEED=0
2. [ ] `check_remote_sha()` type annotation is `str | None`
3. [ ] Fallback log in `clone_repo_cached()` distinguishes network failure from empty SHA
4. [ ] `self_review()` detects empty and unreadable repo_dir

## Self-review

### Verification results
- [ ] Tests: pass/total PASS
- [ ] Validation: intake tests PASS
- [ ] Evidence captured: reports/TC-A05/evidence.md
- [ ] Doc freshness: acknowledged — no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
```

**Expected results**:
- All tests pass
- No regressions introduced

## Integration boundary proven

**Upstream**: `check_remote_sha()` called from `clone_repo_cached()`
**Downstream**: `self_review()` validates IntakeBundle after run completes
**Contract**: `check_remote_sha()` returns `str | None`; `clone_repo_cached()` handles both `None` and `""` identically via `not remote_sha`
