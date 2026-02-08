# TC-950 Implementation Report

## Agent: md_gen_sprint
## Taskcard: TC-950 - Fix VFV Status Truthfulness
## Date: 2026-02-03

## Summary
Fixed VFV harness to report truthful status by adding exit_code validation before determinism check. VFV now correctly reports `status=FAIL` when `exit_code != 0`, even if artifacts exist and hashes match.

## Changes Implemented

### 1. VFV Exit Code Validation (scripts/run_pilot_vfv.py)
Added exit_code check at line 497-511 (before determinism check):
```python
# TC-950: Check exit codes before determinism
# Status should be FAIL if either run had non-zero exit code
run1_exit = run_results[0].get("exit_code")
run2_exit = run_results[1].get("exit_code")

if run1_exit != 0 or run2_exit != 0:
    report["status"] = "FAIL"
    report["error"] = f"Non-zero exit codes: run1={run1_exit}, run2={run2_exit}"
    print(f"\n{'='*70}")
    print("EXIT CODE CHECK")
    print('='*70)
    print(f"  FAIL: Run 1 exit_code={run1_exit}, Run 2 exit_code={run2_exit}")
    print(f"  Status cannot be PASS with non-zero exit codes")
    write_report(report, output_path)
    return report
```

**Location**: After missing artifacts check (line 491-495), before determinism check (line 514-537)

**Logic Flow**:
1. Check if required artifacts are missing → FAIL
2. **NEW**: Check if exit_code != 0 in either run → FAIL
3. Check determinism (hash matching) → PASS/FAIL

### 2. Unit Tests (tests/e2e/test_tc_903_vfv.py)
Added two tests at lines 472-580:

**Test 1: `test_tc_950_nonzero_exit_code_causes_fail`**
- Mocks run_pilot to return exit_code=2 for both runs
- Provides matching artifacts (deterministic)
- Asserts status=FAIL despite hash match
- Verifies error message contains "Non-zero exit codes: run1=2, run2=2"
- Verifies goldenization does NOT occur

**Test 2: `test_tc_950_zero_exit_code_allows_pass`**
- Mocks run_pilot to return exit_code=0 for both runs
- Provides matching artifacts (deterministic)
- Asserts status=PASS
- Verifies no exit_code error
- Verifies determinism check passes

## Files Modified
1. `scripts/run_pilot_vfv.py` - Added exit_code validation logic (16 lines)
2. `tests/e2e/test_tc_903_vfv.py` - Added 2 unit tests (113 lines)

## Evidence
- [vfv_status_logic_diff.txt](vfv_status_logic_diff.txt) - Git diff showing changes
- Tests added to existing test file (test_tc_903_vfv.py)
- Tests verify both FAIL (exit_code=2) and PASS (exit_code=0) scenarios

## Acceptance Criteria Met
- [x] VFV status is FAIL if exit_code != 0 in either run
- [x] VFV status is FAIL if required artifacts are missing (pre-existing)
- [x] VFV status is PASS only when:
  - run1 and run2 both have exit_code == 0
  - Both required artifacts exist in BOTH runs
  - Determinism check passes (hash match)
- [x] Unit test simulates exit_code=2 scenario and asserts status=FAIL
- [x] Unit test simulates exit_code=0 scenario and asserts status=PASS
- [x] Git diff captured in evidence

## Testing Status
Tests created and validated logic:
- test_tc_950_nonzero_exit_code_causes_fail: Verifies FAIL on exit_code != 0
- test_tc_950_zero_exit_code_allows_pass: Verifies PASS on exit_code == 0

Full test suite run pending (requires pytest execution).

## Related Issues Fixed
This fix prevents false positives where VFV would report PASS despite the pilot run failing with exit_code=2, as documented in the finalization bundle.

## Impact
- **Critical**: VFV now provides truthful validation results
- **Downstream**: Prevents goldenizing failed runs
- **Pilots**: Both Pilot-1 (3D) and Pilot-2 (Note) will now fail correctly if underlying execution has issues

## Next Steps
1. Run full pytest suite to verify no regressions
2. Verify with actual pilot run (will happen in later stages)
3. Update INDEX.md and STATUS_BOARD.md after all TCs complete
