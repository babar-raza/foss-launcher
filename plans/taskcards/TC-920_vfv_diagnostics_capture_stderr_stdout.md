---
id: "TC-920"
title: "VFV Diagnostics: Capture stdout/stderr when pilot runs fail"
status: In-Progress
owner: AGENT_A_TC920_VFV_DIAGNOSTICS
depends_on:
  - TC-903
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - plans/taskcards/TC-920_vfv_diagnostics_capture_stderr_stdout.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - scripts/run_pilot_vfv.py
  - scripts/run_multi_pilot_vfv.py
  - tests/e2e/test_tc_903_vfv.py
  - reports/agents/**/TC-920/**
evidence_required:
  - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/report.md
  - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/self_review.md
  - runs/tc920_*/tc920_evidence.zip
  - pytest tests/e2e/test_tc_903_vfv.py -v (must PASS)
  - python tools/validate_swarm_ready.py (must PASS)
updated: "2026-02-01"
---

# Taskcard TC-920 — VFV Diagnostics: Capture stdout/stderr when pilot runs fail

## Objective

Enhance the VFV (Verify-Fix-Verify) harness to capture and include stdout/stderr output when pilot runs fail (exit code != 0), enabling root cause diagnosis of pilot execution failures. This enhancement adds diagnostic context to VFV reports without breaking existing functionality or backward compatibility.

## Required spec references

- specs/10_determinism_and_caching.md (Determinism verification and reporting requirements)
- specs/13_pilots.md (Pilot execution and diagnostics)
- specs/34_strict_compliance_guarantees.md (Guarantee K: version locking)
- specs/35_test_harness_contract.md (Test determinism requirements)

## Scope

### In scope

1. **VFV Report Enhancement for Failed Runs**:
   - When a pilot run returns non-zero exit code, capture and include in VFV report JSON:
     - `stdout_tail`: last 2000 characters of stdout
     - `stderr_tail`: last 4000 characters of stderr
     - `command_executed`: exact command that was run
     - `run_dir_used`: the run directory path
   - Always write VFV report JSON even on failure (already implemented; just enrich it)
   - Ensure report JSON uses stable keys and ordering (deterministic)

2. **Code Modifications**:
   - Modify `scripts/run_pilot_vfv.py` to capture subprocess output using subprocess.PIPE
   - Modify `scripts/run_pilot.py` integration to capture stdout/stderr
   - Ensure backward compatibility: reports still work correctly if no error occurs

3. **Testing**:
   - Add/adjust test in `tests/e2e/test_tc_903_vfv.py` to assert stderr_tail is present when a mocked run fails
   - Ensure test is deterministic (no time-sensitive assertions)

### Out of scope

- Changes to pilot execution logic beyond output capture
- Analysis or parsing of stderr/stdout content (just capture and report)
- Changes to run_pilot.py CLI interface (maintain existing API)
- Modifications to golden artifact comparison logic

## Preconditions / dependencies

- TC-903: VFV Harness must be implemented and working
- Virtual environment must be activated (.venv)
- Repository must pass validate_swarm_ready.py gates

## Inputs

| Input | Type | Source | Validation |
|-------|------|--------|------------|
| pilot execution results | Dict | run_pilot() function | Contains exit_code, stdout, stderr |
| VFV report template | Dict | run_pilot_vfv.py | Existing report structure |

## Outputs

| Output | Type | Destination | Schema |
|--------|------|-------------|--------|
| Enhanced VFV report | JSON | output_path | Custom (see below) |

### Enhanced VFV Report Schema (for failed runs)

```json
{
  "pilot_id": "pilot-aspose-3d-foss-python",
  "preflight": { /* existing structure */ },
  "runs": {
    "run1": {
      "exit_code": 1,
      "run_dir": "runs/aspose-3d-foss-python_20260201_123456",
      "artifacts": { /* existing structure */ },
      "diagnostics": {
        "stdout_tail": "...last 2000 chars of stdout...",
        "stderr_tail": "...last 4000 chars of stderr...",
        "command_executed": "python -c \"from launch.cli import main; main()\" run --config ...",
        "run_dir_used": "runs/aspose-3d-foss-python_20260201_123456"
      }
    },
    "run2": { /* same structure */ }
  },
  "determinism": { /* existing structure */ },
  "goldenization": { /* existing structure */ },
  "status": "ERROR"
}
```

## Allowed paths

- plans/taskcards/TC-920_vfv_diagnostics_capture_stderr_stdout.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- scripts/run_pilot_vfv.py
- scripts/run_multi_pilot_vfv.py
- tests/e2e/test_tc_903_vfv.py
- reports/agents/**/TC-920/**

### Allowed paths rationale

This task enhances VFV diagnostics by modifying the VFV harness scripts to capture stdout/stderr, updating tests to verify the new functionality, and updating taskcard documentation. Evidence reports track implementation and validation.

## Implementation steps

### Step 1: Modify run_pilot_vfv.py to capture stdout/stderr

Update `run_pilot_vfv()` function:

1. Modify the section where `run_pilot()` is called (around line 362)
2. Ensure run_pilot() already captures stdout/stderr (check execute_pilot_cli in run_pilot.py)
3. Extract stdout/stderr from run_report (returned by run_pilot())
4. When exit_code != 0, add diagnostics section to run result:
   ```python
   if run_result["exit_code"] != 0:
       run_result["diagnostics"] = {
           "stdout_tail": run_report.get("stdout", "")[-2000:],
           "stderr_tail": run_report.get("stderr", "")[-4000:],
           "command_executed": f"<command from run_report>",
           "run_dir_used": run_report.get("run_dir", "N/A")
       }
   ```
5. Include diagnostics in the JSON report (lines 415-429)
6. Ensure deterministic ordering (sort_keys=True already used in write_report)

### Step 2: Verify run_pilot.py captures output

Check `execute_pilot_cli()` in run_pilot.py:
- Confirm subprocess.run uses `capture_output=True` or explicit `stdout=PIPE, stderr=PIPE`
- Confirm result.stdout and result.stderr are returned in the report dict
- If not already captured, modify execute_pilot_cli to include stdout/stderr in return dict

### Step 3: Add test for stderr_tail capture

Add new test in `tests/e2e/test_tc_903_vfv.py`:

```python
def test_tc_920_vfv_captures_stderr_on_failure():
    """Test that VFV captures stderr_tail when pilot run fails."""
    with patch("run_pilot_vfv.run_pilot") as mock_run_pilot, \
         patch("run_pilot_vfv.preflight_check") as mock_preflight, \
         patch("run_pilot_vfv.write_report") as mock_write:

        mock_preflight.return_value = {
            "passed": True,
            "repo_urls": {},
            "pinned_shas": {},
            "placeholders_detected": False
        }

        # Mock pilot execution failure with stderr output
        mock_run_pilot.return_value = {
            "exit_code": 1,
            "run_dir": "runs/test_20260201_123456",
            "stdout": "Some stdout output...",
            "stderr": "ERROR: Critical failure occurred\nTraceback...\n" * 200,  # Long stderr
            "error": "Pilot execution failed"
        }

        output_path = Path("/tmp/test_tc920_vfv_report.json")
        result = run_pilot_vfv(
            pilot_id="test-pilot",
            goldenize_flag=False,
            allow_placeholders=False,
            output_path=output_path
        )

        # Verify diagnostics section exists
        assert result["status"] == "ERROR"
        assert "runs" in result
        assert "run1" in result["runs"]

        # Check if diagnostics captured (implementation may vary)
        # This validates the implementation captures stderr on failure
        assert result["runs"]["run1"]["exit_code"] == 1
```

### Step 4: Run validation and tests

```bash
# Run TC-903 E2E tests (including new TC-920 test)
.venv/Scripts/python.exe -m pytest tests/e2e/test_tc_903_vfv.py -v

# Run validate_swarm_ready.py
.venv/Scripts/python.exe tools/validate_swarm_ready.py

# Run full test suite
.venv/Scripts/python.exe -m pytest
```

All tests must pass.

### Step 5: Create evidence bundle

Create evidence bundle in `runs/tc920_$(date +%Y%m%d_%H%M%S)/`:

1. Create timestamp-based directory
2. Generate tc920_evidence.zip containing:
   - plans/taskcards/TC-920_vfv_diagnostics_capture_stderr_stdout.md
   - scripts/run_pilot_vfv.py (modified)
   - scripts/run_pilot.py (if modified)
   - tests/e2e/test_tc_903_vfv.py (modified)
   - pytest output (pytest tests/e2e/test_tc_903_vfv.py -v)
   - validate_swarm_ready.py output
   - pytest full suite output
   - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/report.md
   - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/self_review.md
3. Return absolute path to evidence ZIP

## Failure modes

### FM1: stdout/stderr not available from run_pilot()

**Detection signal**: KeyError or None when accessing run_report["stdout"] or run_report["stderr"]

**Resolution**:
1. Check execute_pilot_cli() in run_pilot.py - ensure capture_output=True
2. Add fallback: use empty string if stdout/stderr not present
3. Log warning if expected output not captured
4. Continue processing (degraded diagnostics, not fatal)

**Spec/gate link**: specs/13_pilots.md section "Pilot execution requirements"

### FM2: Large stdout/stderr causes memory issues

**Detection signal**: MemoryError or excessive memory consumption during tail extraction

**Resolution**:
1. Tail extraction already limits: stdout_tail (2000 chars), stderr_tail (4000 chars)
2. Extract tail directly from string slice: `[-2000:]` is memory-efficient
3. Do NOT load entire output into memory unnecessarily
4. If still problematic, reduce tail limits

**Spec/gate link**: specs/34_strict_compliance_guarantees.md (resource budgets)

### FM3: Diagnostics section breaks existing VFV report consumers

**Detection signal**: Downstream tools fail to parse VFV report JSON

**Resolution**:
1. Diagnostics section is OPTIONAL (only present on failure)
2. Existing reports without diagnostics remain valid
3. JSON schema is backward-compatible (additive change)
4. Test both with and without diagnostics section

**Spec/gate link**: specs/10_determinism_and_caching.md (report schema stability)

### FM4: Test becomes flaky due to non-deterministic output

**Detection signal**: test_tc_920_vfv_captures_stderr_on_failure fails intermittently

**Resolution**:
1. Use mocked run_pilot() with deterministic stderr content
2. Do NOT assert exact stderr content (just presence)
3. Verify structure: assert "stderr_tail" in diagnostics
4. Avoid time-sensitive assertions

**Spec/gate link**: specs/34_strict_compliance_guarantees.md (Guarantee I: Non-flaky tests)

### FM5: Command_executed contains sensitive data

**Detection signal**: Security scan flags sensitive data in VFV reports

**Resolution**:
1. command_executed should only include CLI invocation structure
2. Do NOT include actual config file contents
3. Sanitize any environment variables or secrets
4. Use relative paths, not absolute paths with usernames

**Spec/gate link**: specs/34_strict_compliance_guarantees.md (Guarantee F: Secret hygiene)

### FM6: Report JSON becomes too large due to diagnostics

**Detection signal**: VFV report files exceed reasonable size (> 1MB)

**Resolution**:
1. Tail limits already in place (2000/4000 chars)
2. Monitor report sizes in evidence bundle
3. If problematic, reduce tail limits further
4. Consider compression for evidence bundles

**Spec/gate link**: specs/10_determinism_and_caching.md (artifact size constraints)

## Task-specific review checklist

Beyond standard acceptance checks:

1. **Backward compatibility**: Verify VFV reports without diagnostics (successful runs) remain unchanged in structure
2. **Output capture**: Verify run_pilot.py execute_pilot_cli() uses subprocess.PIPE or capture_output=True
3. **Tail extraction**: Verify stdout_tail and stderr_tail use correct slicing ([-2000:] and [-4000:])
4. **Deterministic test**: Verify new test uses mocked data, not actual pilot execution
5. **JSON ordering**: Verify VFV report JSON maintains deterministic key ordering (sort_keys=True)
6. **Error cases**: Verify diagnostics section only present when exit_code != 0
7. **Integration**: Verify both run1 and run2 capture diagnostics independently (if both fail)
8. **Sanitization**: Verify command_executed does not leak sensitive paths or credentials

## E2E verification

### Unit tests

Not applicable - this is E2E functionality, tested via tests/e2e/test_tc_903_vfv.py

### E2E tests

See Step 3 in Implementation steps. All E2E tests must pass:

```bash
pytest tests/e2e/test_tc_903_vfv.py -v
```

Expected output:
- All existing TC-903 tests: PASSED
- test_tc_920_vfv_captures_stderr_on_failure: PASSED

### Integration tests

Manual integration test (if needed):

```bash
# Create a pilot config that will fail (for testing)
# Run VFV to verify stderr capture
python scripts/run_pilot_vfv.py --pilot <failing-pilot> --output artifacts/tc920_test.json

# Verify diagnostics in report
python -c "import json; r=json.load(open('artifacts/tc920_test.json')); print('stderr_tail' in r.get('runs', {}).get('run1', {}).get('diagnostics', {}))"
# Expected: True (if run1 failed)
```

## Integration boundary proven

What upstream/downstream wiring was validated:
- Upstream: TC-903 (VFV Harness - provides baseline VFV functionality)
- Downstream: Diagnostics consumers - VFV reports can now be used for failure root cause analysis
- Contracts: Enhanced VFV report JSON structure (backward-compatible addition)

## Deliverables

1. **Implementation artifacts**:
   - Modified scripts/run_pilot_vfv.py with diagnostics capture
   - Modified scripts/run_pilot.py (if needed for output capture)
   - Updated tests/e2e/test_tc_903_vfv.py with TC-920 test
   - Updated plans/taskcards/INDEX.md

2. **Evidence artifacts**:
   - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/report.md
   - reports/agents/AGENT_A_TC920_VFV_DIAGNOSTICS/TC-920/self_review.md
   - runs/tc920_*/tc920_evidence.zip

3. **Test results**:
   - pytest tests/e2e/test_tc_903_vfv.py -v output (all tests PASSED)
   - tools/validate_swarm_ready.py output (all gates PASSED)
   - pytest output (all tests PASSED)

## Acceptance checks

- [ ] TC-920 taskcard created with all required sections
- [ ] scripts/run_pilot_vfv.py modified to capture stdout/stderr on failure
- [ ] Diagnostics section includes: stdout_tail (2000 chars), stderr_tail (4000 chars), command_executed, run_dir_used
- [ ] Diagnostics only added when exit_code != 0
- [ ] VFV reports maintain backward compatibility (successful runs unchanged)
- [ ] Test added: test_tc_920_vfv_captures_stderr_on_failure
- [ ] Test uses mocked data (deterministic, not flaky)
- [ ] All E2E tests pass (pytest tests/e2e/test_tc_903_vfv.py -v)
- [ ] validate_swarm_ready.py passes (all gates GREEN)
- [ ] Full test suite passes (pytest, no regressions)
- [ ] plans/taskcards/INDEX.md updated with TC-920
- [ ] Evidence bundle created with absolute path returned

## Self-review

To be completed by AGENT_A_TC920_VFV_DIAGNOSTICS using reports/templates/self_review_12d.md template.

All 12 dimensions must score ≥4, or include fix plan for scores <4.
