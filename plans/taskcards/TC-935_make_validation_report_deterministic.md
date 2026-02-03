# TC-935: Make validation_report.json Deterministic

**Status:** ACTIVE
**Priority:** P0 (Blocks VFV goldenization)
**Created:** 2026-02-03
**Agent:** tc935_w7_determinism_then_goldenize_20260203_090328

## Problem Statement

Pilot VFV (Verify-Fix-Verify) goldenization is blocked because validation_report.json is non-deterministic across runs. The report contains absolute file paths with run-specific timestamps embedded in the run directory name, causing different SHA256 hashes for identical validation results.

**Evidence:**
- Run1 SHA256: `c2ebfda64a21770233ad98e3e01fcf4fefa4070789f209744979f36a6a6b8ba8`
- Run2 SHA256: `dfcd19926d19654810892faa87ddb03acdc928904b9628dda73a9209433db173`
- Root cause: Paths like `runs\r_20260203T025743Z_launch_pilot-aspose-3d-foss-python_...` differ by timestamp

## Objective

Make validation_report.json deterministic by normalizing absolute paths to relative paths (or stable placeholders) and ensuring deterministic list ordering, without losing validation information.

## Acceptance Criteria

1. ✓ validation_report.json contains no run-specific absolute paths or timestamps
2. ✓ Two simulated runs with different run_dir produce identical canonical JSON SHA256
3. ✓ Pilot-1 VFV determinism check PASS for validation_report.json
4. ✓ validate_swarm_ready remains PASS (all 21 gates)
5. ✓ pytest PASS (all unit tests including TC-935 test)

## Allowed File Modifications

- `plans/taskcards/TC-935_make_validation_report_deterministic.md` (this file)
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `src/launch/workers/w7_validator/worker.py`
- `src/launch/workers/w7_validator/reporting.py` (if validation report writing is delegated)
- `specs/schemas/validation_report.schema.json` (only if needed to clarify field expectations)
- `tests/unit/workers/test_tc_935_validation_report_determinism.py`
- `reports/agents/**/TC-935/**`

## Implementation Plan

### 1. Locate Validation Report Writing Code
Search for where validation_report.json is assembled and written:
```bash
rg -n "validation_report\.json|write_validation_report|ValidationReport" src/launch/workers/w7_validator -S
```

### 2. Implement Normalization Logic
Add `normalize_report(report: dict, run_dir: Path) -> dict` helper that:
- **Normalizes absolute paths:**
  - Strip run_dir prefix from all file paths
  - Convert to relative paths (e.g., `artifacts/page_plan.json`)
  - OR replace with `<RUN_DIR>/...` placeholder
- **Removes/nullifies timestamps:**
  - Set timestamp fields to `null` or stable placeholder
  - Document which fields are affected
- **Sorts lists deterministically:**
  - Sort violation lists by: `rule_id`, then `path`, then `line`
  - Sort file lists alphabetically
  - Use `json.dumps(sort_keys=True)` for output

### 3. Apply Normalization Before Writing
Modify W7 worker to call `normalize_report()` before writing validation_report.json:
```python
normalized = normalize_report(raw_report, run_dir)
with open(report_path, "w") as f:
    json.dump(normalized, f, indent=2, sort_keys=True)
```

### 4. Unit Test Coverage
Create `tests/unit/workers/test_tc_935_validation_report_determinism.py`:
- Test case: Build sample report with:
  - Absolute path containing run_dir
  - Timestamp string
  - Unordered list of violations
- Call `normalize_report()` twice with different run_dir values
- Assert: Canonical JSON SHA256 hashes match

## Test Verification

```powershell
# Run TC-935 unit test
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_935_validation_report_determinism.py -q

# Run full test suite
.venv\Scripts\python.exe -m pytest -q

# Run validation gates
.venv\Scripts\python.exe tools/validate_swarm_ready.py
```

## Dependencies

- None (isolated W7 worker change)

## Risk Assessment

**Low Risk:**
- Change is isolated to validation report formatting
- Does not affect validation logic or rule execution
- Normalization is applied after validation completes
- Unit test provides determinism guarantee

## Notes

- Do NOT mask or redact fields; normalize deterministically with explicit rules
- Preserve all validation information; only format changes for determinism
- This fix unblocks VFV goldenization for Pilot-1 and Pilot-2

## Evidence Location

`runs/tc935_w7_determinism_then_goldenize_20260203_090328/`
