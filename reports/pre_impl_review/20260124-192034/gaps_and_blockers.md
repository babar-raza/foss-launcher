# Gaps and Blockers

**Timestamp**: 20260124-192034
**Status**: **BLOCKED** - Cannot merge to main

---

## OPEN BLOCKERS

### Blocker 1: Console Script Tests Failing
**File**: [tests/unit/test_tc_530_entrypoints.py](../../../tests/unit/test_tc_530_entrypoints.py)
**Status**: OPEN
**Severity**: HIGH

**Description**:
Three console script tests are failing with `FileNotFoundError`:
- `test_launch_run_console_script_help`
- `test_launch_validate_console_script_help`
- `test_launch_mcp_console_script_help`

**Error**: `FileNotFoundError: [WinError 2] The system cannot find the file specified`

**Root Cause**: The console script executables (`launch_run.exe`, `launch_validate.exe`, `launch_mcp.exe`) are not being found in the `.venv/Scripts/` directory even after installing the package in editable mode.

**Impact**: Prevents pytest from passing, which is a GO requirement.

---

### Blocker 2: Diff Analyzer Test Failures
**File**: [tests/unit/util/test_diff_analyzer.py](../../../tests/unit/util/test_diff_analyzer.py)
**Status**: OPEN
**Severity**: HIGH

**Description**:
Five diff analyzer tests are failing:
- `TestFormattingDetection::test_detect_whitespace_only_change`
- `TestLineCounting::test_count_additions`
- `TestLineCounting::test_count_deletions`
- `TestFileChangeAnalysis::test_analyze_under_budget`
- `TestFileChangeAnalysis::test_analyze_exceeds_budget`

**Failure Examples**:
```
assert detect_formatting_only_changes('def foo():\n    return 42', 'def foo():\n        return 42') is True
AssertionError: assert False is True

assert added == 2
AssertionError: assert 3 == 2
```

**Root Cause**: The diff analyzer logic appears to have bugs or the tests have incorrect expectations.

**Impact**: Prevents pytest from passing, which is a GO requirement.

---

## RESOLVED BLOCKERS

None yet.

---

## TESTING EVIDENCE

### Phase 3 Test Run (PYTHONHASHSEED=0)
**Command**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -q`
**Result**: FAILED - 8 failures, 149 passed
**Exit Code**: 1

**Failed Tests**:
1. tests/unit/test_tc_530_entrypoints.py::test_launch_run_console_script_help
2. tests/unit/test_tc_530_entrypoints.py::test_launch_validate_console_script_help
3. tests/unit/test_tc_530_entrypoints.py::test_launch_mcp_console_script_help
4. tests/unit/util/test_diff_analyzer.py::TestFormattingDetection::test_detect_whitespace_only_change
5. tests/unit/util/test_diff_analyzer.py::TestLineCounting::test_count_additions
6. tests/unit/util/test_diff_analyzer.py::TestLineCounting::test_count_deletions
7. tests/unit/util/test_diff_analyzer.py::TestFileChangeAnalysis::test_analyze_under_budget
8. tests/unit/util/test_diff_analyzer.py::TestFileChangeAnalysis::test_analyze_exceeds_budget

---

## GO RULE COMPLIANCE CHECK

**GO RULE REQUIREMENTS**:
- ✅ check_markdown_links passes
- ✅ validate_swarm_ready passes when run from .venv (all 19 gates passed)
- ❌ pytest passes with PYTHONHASHSEED=0 (FAILED - 8 test failures)

**RESULT**: **NO-GO** - pytest requirement not met
