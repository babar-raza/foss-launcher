---
id: TC-950
title: "Fix VFV Status Truthfulness"
status: Draft
priority: Critical
owner: "VFV_FIXER"
updated: "2026-02-03"
tags: ["vfv", "validation", "determinism", "exit-code", "pilot"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-950_fix_vfv_status_truthfulness.md
  - scripts/run_pilot_vfv.py
  - scripts/run_multi_pilot_vfv.py
  - tests/e2e/test_pilot_vfv.py
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-950/**
evidence_required:
  - reports/agents/<agent>/TC-950/report.md
  - reports/agents/<agent>/TC-950/self_review.md
  - reports/agents/<agent>/TC-950/test_output.txt
  - reports/agents/<agent>/TC-950/vfv_status_logic_diff.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-950: Fix VFV Status Truthfulness

## Objective
Fix VFV (Verification for Validation) to correctly report status=FAIL when exit_code is non-zero, preventing false positives where determinism passes but pilots actually failed.

## Problem Statement
VFV currently reports `status=PASS` even when `exit_code=2`, as long as artifacts exist and hashes match. This is a false positive that hides real failures.

**Evidence from finalization bundle:**
- VFV JSON shows `exit_code=2` while `status=PASS`
- Root cause: Line 527-536 in [scripts/run_pilot_vfv.py](scripts/run_pilot_vfv.py#L527-L536) only checks determinism (hash matching), not exit codes

## Required spec references
- specs/34_strict_compliance_guarantees.md (VFV determinism requirements)
- specs/10_determinism_and_caching.md (Exit code handling in deterministic operations)

## Scope

### In scope
- Add exit_code validation to VFV status logic before determinism check
- Ensure status=FAIL if either run1 or run2 has exit_code != 0
- Ensure status=FAIL if required artifacts are missing
- Add unit test simulating exit_code=2 scenario
- Maintain determinism check for successful runs (both exit_code=0)

### Out of scope
- Changes to pilot configurations
- Modifications to artifact generation logic
- Changes to determinism checking algorithm (hash matching)

## Inputs
- Current scripts/run_pilot_vfv.py with buggy status logic (lines 527-536)
- VFV JSON report showing exit_code=2 with status=PASS
- Pilot run artifacts with matching hashes but non-zero exit codes

## Outputs
- Fixed scripts/run_pilot_vfv.py with exit_code check before determinism
- Unit test in tests/e2e/test_pilot_vfv.py covering exit_code=2 scenario
- VFV reports showing status=FAIL when exit_code != 0
- Test output log showing new test passing

## Acceptance Criteria
1. VFV status is `FAIL` if exit_code != 0 in either run
2. VFV status is `FAIL` if required artifacts are missing
3. VFV status is `PASS` only when:
   - run1 and run2 both have `exit_code == 0`
   - Both required artifacts exist in BOTH runs
   - Determinism check passes (hash match)
4. Unit test simulates exit_code=2 scenario and asserts `status=FAIL`
5. Gate K (if applicable) passes after fix

## Allowed paths

- `plans/taskcards/TC-950_fix_vfv_status_truthfulness.md`
- `scripts/run_pilot_vfv.py`
- `scripts/run_multi_pilot_vfv.py`
- `tests/e2e/test_pilot_vfv.py`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-950/**`## Implementation steps

### Step 1: Analyze current buggy logic
Read scripts/run_pilot_vfv.py lines 527-536 to understand the determinism check:

Current Buggy Logic (lines 527-536):
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

### Step 2: Add exit_code validation
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

### Step 3: Add unit test
Add test in `tests/e2e/test_pilot_vfv.py` that:
1. Mocks `run_pilot()` to return exit_code=2 for both runs
2. Provides valid artifacts with matching hashes
3. Asserts final status is "FAIL" despite hash match
4. Verifies error message mentions non-zero exit codes

### Step 4: Run tests and validation
```bash
.venv/Scripts/python.exe -m pytest tests/e2e/test_pilot_vfv.py -v
.venv/Scripts/python.exe tools/validate_swarm_ready.py
```

## Task-specific review checklist
1. [ ] Exit_code check added before determinism logic in run_pilot_vfv.py
2. [ ] Both run1 and run2 exit codes are checked (not just one)
3. [ ] Status set to FAIL if either exit_code != 0
4. [ ] Error message includes both exit codes for debugging
5. [ ] Determinism check still runs when both exit codes are 0
6. [ ] Unit test creates mock runs with exit_code=2 and matching hashes
7. [ ] Unit test verifies status="FAIL" despite determinism passing
8. [ ] Git diff captured showing exact lines changed
9. [ ] validate_swarm_ready shows no regressions after fix
10. [ ] Pilot VFV runs correctly fail when exit_code != 0

## Failure modes

### Failure mode 1: VFV still reports PASS despite non-zero exit code
**Detection:** VFV JSON shows status=PASS with exit_code=2 or exit_code=1
**Resolution:** Verify exit_code check is positioned BEFORE determinism check in code flow; ensure early return after setting status=FAIL; check that exit_code values are extracted correctly from run_results
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (VFV truthfulness requirements)

### Failure mode 2: VFV incorrectly fails when both runs have exit_code=0
**Detection:** VFV reports status=FAIL despite both runs completing successfully with exit_code=0 and matching hashes
**Resolution:** Verify exit_code check uses `!= 0` comparison, not `> 0` or other logic; ensure the check only triggers on non-zero values; verify None/missing exit_code is handled appropriately
**Spec/Gate:** specs/10_determinism_and_caching.md (Deterministic success criteria)

### Failure mode 3: Unit test fails due to incorrect mock setup
**Detection:** pytest shows test_vfv_exit_code_2_fails() failing with assertion errors or mock-related exceptions
**Resolution:** Ensure mock run_pilot() returns dict with exit_code=2 field; verify artifact generation includes matching hashes; check that VFV reads exit_code from correct location in run_results structure
**Spec/Gate:** Test contract for VFV harness

## Deliverables
- Modified scripts/run_pilot_vfv.py with exit_code validation
- Modified scripts/run_multi_pilot_vfv.py if applicable
- New unit test in tests/e2e/test_pilot_vfv.py
- reports/agents/<agent>/TC-950/vfv_status_logic_diff.txt (git diff)
- reports/agents/<agent>/TC-950/test_output.txt (pytest output)
- reports/agents/<agent>/TC-950/report.md
- reports/agents/<agent>/TC-950/self_review.md

## Acceptance checks
- [ ] exit_code check added before determinism logic
- [ ] Unit test covers exit_code=2 scenario
- [ ] Test output shows new test passing
- [ ] git diff captured in evidence
- [ ] validate_swarm_ready and pytest fully green
- [ ] Report and self-review written

## E2E verification
Run VFV with both pilots:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python
```

Expected artifacts:
- VFV JSON report with status=FAIL when exit_code != 0
- VFV JSON report with status=PASS when exit_code=0 and determinism passes
- Error field populated with exit code values when status=FAIL

## Integration boundary proven
**Upstream:** Pilot execution (run_pilot.py or scripts) provides run_results dict with exit_code field to VFV harness
**Downstream:** VFV harness reports status to goldenization logic and CI/CD pipeline; FAIL status blocks golden file updates
**Contract:** VFV must check exit_code before determinism; status=PASS requires both exit_code=0 AND determinism=PASS

## Self-review
- [ ] Exit_code validation positioned correctly (before determinism check)
- [ ] Both run1 and run2 exit codes checked
- [ ] Unit test verifies false positive scenario (exit_code=2 with matching hashes)
- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
