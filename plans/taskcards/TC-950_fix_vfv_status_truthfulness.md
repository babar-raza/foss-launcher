# TC-950: Fix VFV Status Truthfulness

## Metadata
- **Status**: Ready
- **Owner**: VFV_FIXER
- **Depends On**: -
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
VFV currently reports `status=PASS` even when `exit_code=2`, as long as artifacts exist and hashes match. This is a false positive that hides real failures.

**Evidence from finalization bundle:**
- VFV JSON shows `exit_code=2` while `status=PASS`
- Root cause: Line 527-536 in [scripts/run_pilot_vfv.py](scripts/run_pilot_vfv.py#L527-L536) only checks determinism (hash matching), not exit codes

## Acceptance Criteria
1. VFV status is `FAIL` if exit_code != 0 in either run
2. VFV status is `FAIL` if required artifacts are missing
3. VFV status is `PASS` only when:
   - run1 and run2 both have `exit_code == 0`
   - Both required artifacts exist in BOTH runs
   - Determinism check passes (hash match)
4. Unit test simulates exit_code=2 scenario and asserts `status=FAIL`
5. Gate K (if applicable) passes after fix

## Allowed Paths
- plans/taskcards/TC-950_fix_vfv_status_truthfulness.md
- scripts/run_pilot_vfv.py
- scripts/run_multi_pilot_vfv.py
- tests/e2e/test_pilot_vfv.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-950/**

## Evidence Requirements
- reports/agents/<agent>/TC-950/report.md
- reports/agents/<agent>/TC-950/self_review.md
- reports/agents/<agent>/TC-950/test_output.txt (pytest showing new test)
- reports/agents/<agent>/TC-950/vfv_status_logic_diff.txt (git diff of the fix)

## Implementation Notes

### Current Buggy Logic (lines 527-536)
```python
if all_match:
    report["determinism"]["status"] = "PASS"
    report["status"] = "PASS"
    print(f"\nDeterminism: PASS")
else:
    report["determinism"]["status"] = "FAIL"
    report["status"] = "FAIL"
    print(f"\nDeterminism: FAIL")
```

### Required Fix
Add exit_code validation BEFORE determinism check:
```python
# Check exit codes first
run1_exit = run_results[0].get("exit_code")
run2_exit = run_results[1].get("exit_code")

if run1_exit != 0 or run2_exit != 0:
    report["status"] = "FAIL"
    report["error"] = f"Non-zero exit codes: run1={run1_exit}, run2={run2_exit}"
    write_report(report, output_path)
    return report

# Then check determinism
if all_match:
    report["determinism"]["status"] = "PASS"
    report["status"] = "PASS"
    print(f"\nDeterminism: PASS")
else:
    report["determinism"]["status"] = "FAIL"
    report["status"] = "FAIL"
    print(f"\nDeterminism: FAIL")
```

### Test Requirements
Add test in `tests/e2e/test_pilot_vfv.py` that:
1. Mocks `run_pilot()` to return exit_code=2 for both runs
2. Provides valid artifacts with matching hashes
3. Asserts final status is "FAIL" despite hash match
4. Verifies error message mentions non-zero exit codes

## Dependencies
None

## Related Issues
- AG-001 approval gate blocks PR creation (TC-951)
- No visible .md files (TC-952)
- Minimal page inventory (TC-953)

## Definition of Done
- [ ] exit_code check added before determinism logic
- [ ] Unit test covers exit_code=2 scenario
- [ ] Test output shows new test passing
- [ ] git diff captured in evidence
- [ ] validate_swarm_ready and pytest fully green
- [ ] Report and self-review written
