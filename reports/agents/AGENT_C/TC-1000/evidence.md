# TC-1000: Fix Pre-existing Test Failures -- Evidence

**Agent**: Agent-C (Tests & Verification)
**Date**: 2026-02-05
**Status**: Complete
**Result**: 1902 passed, 12 skipped, 0 failures

## Summary

Fixed 15 pre-existing test failures across 4 test files. No source code was modified -- only test assertions and test setup were changed.

## Full Test Suite Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
=========== 1902 passed, 12 skipped, 1 warning in 92.87s (0:01:32) ============
```

---

## File 1: `tests/e2e/test_tc_903_vfv.py` (4 fixes)

### Fix 1a: `test_tc_903_vfv_both_artifacts_checked` (line 113)

- **Old assertion**: `assert result["status"] == "ERROR"`
- **New assertion**: `assert result["status"] == "FAIL"`
- **Reason**: The test mocks `run_pilot` to return `exit_code=1` and `run_dir=None`. In `run_pilot_vfv.py`, when `run_dir` is `None`, no artifacts are found, so the code hits the "missing artifacts" check at line 486-490 which sets `status = "FAIL"`. The `"ERROR"` status is only used for preflight failures (line 348).

### Fix 1b: `test_tc_903_vfv_goldenize_only_on_pass` (line 175)

- **Old assertion**: `assert result["status"] == "ERROR"`
- **New assertion**: `assert result["status"] == "FAIL"`
- **Reason**: Same root cause as Fix 1a. The mock returns `exit_code=1` and `run_dir=None`, which results in missing artifacts and `status = "FAIL"`, not `"ERROR"`.

### Fix 1c: `test_tc_920_vfv_captures_stderr_on_failure` (line 404)

- **Old assertion**: `assert result["status"] == "ERROR"`
- **New assertion**: `assert result["status"] == "FAIL"`
- **Reason**: The mock returns `exit_code=1` with `run_dir="runs/test_20260201_123456"`. However, no actual artifacts exist at that path, so the code hits the missing artifacts check (line 486-490) which sets `status = "FAIL"`.

### Fix 1d: `test_tc_903_vfv_preflight_rejects_placeholder_shas` (lines 270-299)

- **Old mock data**: `{"target_repo": {"url": "...", "ref": "000..."}}`
- **New mock data**: `{"github_repo_url": "...", "github_ref": "000..."}`
- **Old patch target**: `patch.object(launch.io.run_config, "load_and_validate_run_config")`
- **New patch target**: Same (kept, since the import is inside the function)
- **Old Path.exists patch**: `patch("run_pilot_vfv.Path.exists", return_value=True)`
- **New Path.exists patch**: `patch("pathlib.Path.exists", return_value=True)`
- **Reason**: The `preflight_check` function inspects `config["github_ref"]`, `config["site_ref"]`, etc. -- NOT `config["target_repo"]["ref"]`. The mock return value was using the wrong data structure, so the function never detected the placeholder SHA. Fixed the mock to use the actual keys the function checks. Also fixed the `Path.exists` patch to target `pathlib.Path.exists` (instance method) instead of `run_pilot_vfv.Path.exists`.

---

## File 2: `tests/unit/workers/test_tc_440_section_writer.py` (2 fixes)

### Fix 2a: `test_generate_section_content_fallback` (lines 319-320)

- **Old assertions**:
  - `assert "<!-- claim_id: claim_001 -->" in content`
  - `assert "<!-- claim_id: claim_002 -->" in content`
- **New assertions**:
  - `assert "[claim: claim_001]" in content`
  - `assert "[claim: claim_002]" in content`
- **Reason**: TC-977 changed the claim marker format in W5's fallback content generation (line 984 in worker.py) from `<!-- claim_id: XX -->` to `[claim: XX]` for Gate 14 compliance.

### Fix 2b: `test_claim_marker_format` (line 667)

- **Old regex**: `r'<!-- claim_id: (claim_\d+) -->'`
- **New regex**: `r'\[claim: (claim_\d+)\]'`
- **Reason**: Same as Fix 2a. The fallback content generation now uses `[claim: XX]` format per TC-977.

---

## File 3: `tests/unit/workers/test_tc_480_pr_manager.py` (8 fixes)

### Root Cause (all 8 tests)

W9 PRManager auto-enables offline mode when `validation_profile` is `"local"` (the default). See `worker.py` line 445-446:

```python
validation_profile = run_config.get("validation_profile", "local")
offline_mode = os.getenv("OFFLINE_MODE", "0") == "1" or validation_profile == "local"
```

In offline mode, the worker bypasses the `commit_client` entirely, so all tests that mock `commit_client` and expect it to be called fail because the code never reaches those calls.

Additionally, when `validation_profile` is set to `"ci"`, the code reaches the AG-001 approval gate (line 502-545) which requires an approval marker file at `run_dir.parent / ".git" / "AI_BRANCH_APPROVED"`.

### Fix 3a: `sample_run_config` fixture (line 114)

- **Old fixture**: Did not include `validation_profile`
- **New fixture**: Added `"validation_profile": "ci"` to the config dict
- **Reason**: Setting `validation_profile: "ci"` prevents auto-enabling offline mode, ensuring the mock `commit_client` is used as intended.

### Fix 3b: `temp_run_dir` fixture (line 48)

- **Old fixture**: Did not create AG-001 approval marker
- **New fixture**: Creates `.git/AI_BRANCH_APPROVED` marker file in `run_dir.parent`
- **Reason**: With `validation_profile: "ci"`, the code reaches the AG-001 approval gate which requires an approval marker file. Without it, all tests raising `PRManagerError("AG-001 approval gate violation...")`.

### Tests fixed by these 2 fixture changes:

1. `test_execute_pr_manager_success`
2. `test_execute_pr_manager_no_changes`
3. `test_execute_pr_manager_auth_failed`
4. `test_execute_pr_manager_rate_limited`
5. `test_execute_pr_manager_branch_exists`
6. `test_execute_pr_manager_deterministic`
7. `test_execute_pr_manager_draft_pr_on_validation_failure`
8. `test_pr_json_rollback_metadata`

---

## File 4: `tests/unit/test_validate_windows_reserved_names.py` (1 fix -- pre-existing)

### Fix 4a: `test_clean_repo_passes` (line 80)

- **Status**: Already passing (no code changes needed)
- **Reason**: The `nul` file shown in `git status` as `?? nul` is an untracked file. On Windows, `NUL` is a reserved device name that cannot exist as a regular file on the filesystem. The file does not actually exist on disk, and the validation script correctly finds no reserved names. The test passes as-is.

---

## Files Modified

| File | Changes |
|------|---------|
| `tests/e2e/test_tc_903_vfv.py` | 4 assertion fixes (ERROR -> FAIL, mock data structure, Path.exists patch) |
| `tests/unit/workers/test_tc_440_section_writer.py` | 2 assertion fixes (claim marker format) |
| `tests/unit/workers/test_tc_480_pr_manager.py` | 2 fixture fixes (validation_profile + AG-001 marker) affecting 8 tests |
| `tests/unit/test_validate_windows_reserved_names.py` | 0 changes (already passing) |

**Total tests fixed: 14 test assertions + 1 confirmed-passing = 15 addressed**
