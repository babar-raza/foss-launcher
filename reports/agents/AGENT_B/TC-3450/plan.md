# Agent B — TC-3450 — W10 Stale Path Guard

## Task
Add a stale-path guard in `execute_fixer()` that raises `StaleValidationReportError` when `issue.location.path` no longer exists on disk, instead of falling through to apply_fix() and returning `status:"unfixable"`.

## Assumptions (verified)
- `StaleValidationReportError` already defined at `w10_fixer/worker.py:124`
- `emit_event()` already defined at `w10_fixer/worker.py:191`
- `EVENT_FIXER_STALE_PATH_DETECTED` does not exist yet (confirmed by grep)
- No new imports needed

## Steps
1. Add `EVENT_FIXER_STALE_PATH_DETECTED = "FIXER_STALE_PATH_DETECTED"` before `# Exception hierarchy`
2. Insert 22-line stale path guard in `execute_fixer()` after `_normalize_issue_paths(issue, run_dir)`
3. Add `StaleValidationReportError` to test imports
4. Update `test_truly_missing_file_clear_error` to use `pytest.raises(StaleValidationReportError)`
5. Add `TestStalePathGuard` class (4 deterministic tests)

## Rollback
Revert 3 edits to `w10_fixer/worker.py` + test file. No schema changes.

## Acceptance checklist
- [ ] EVENT constant defined before use
- [ ] Guard placed AFTER `_normalize_issue_paths()` (path fully resolved)
- [ ] Guard placed BEFORE `FIXER_STARTED` event (no partial logging)
- [ ] `isinstance` guard on `_stale_loc` prevents AttributeError
- [ ] Exception message includes issue_id + resolved path
- [ ] 26 tests pass in `test_w10_path_normalization.py`
- [ ] Full suite: 0 new failures
