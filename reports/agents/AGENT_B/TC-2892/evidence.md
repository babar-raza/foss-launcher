# TC-2892 Evidence: FQ-8 Bake-in + Severity Promotion

## Summary
Ran all 3 pilots to validate FQ-8 adjacent fence detection produces zero false merges,
then promoted severity from `warn` to `error`.

## Bake-in Evidence (3/3 pilots clean)

| Pilot | Run ID | FQ-8 Hits | Adjacent Fences in Final Output | False Merges | Result |
|-------|--------|-----------|---------------------------------|-------------|--------|
| aspose-3d | `r_20260226T211200Z_..._c593a2ed` | 0 | 0 / 27 files | 0 | PASS |
| aspose-note | `r_20260226T214401Z_..._61d152a7` | 0 | 0 / 28 files | 0 | PASS |
| aspose-cells | `r_20260226T220459Z_..._b5399032` | 0 | 0 / 38 files | 0 | PASS |

**Total files scanned**: 93 markdown files across 3 pilots
**Total FQ-8 false positives**: 0
**Total false merges**: 0

Detailed evidence per pilot:
- `plans/healing/evidence/TC-2892_bakein_aspose-3d_r_20260226T211200Z.md`
- `plans/healing/evidence/TC-2892_bakein_aspose-note_r_20260226T214401Z.md`
- `plans/healing/evidence/TC-2892_bakein_aspose-cells_r_20260226T220459Z.md`

## Code Changes

### gate_17_prelints.py
1. **Severity**: `"severity": "warn"` → `"severity": "error"` (line 291)
2. **_ERROR_CODES**: Added `"G17-FQ-8"` to frozenset (line 415)
3. **Docstring**: Updated to reflect promotion (lines 237-238)

### test_gate_17_fq8.py
1. `test_adjacent_python_fences_detected`: severity assertion `"warn"` → `"error"` (line 32)
2. `test_integrated_in_run_deterministic`: `has_errors is False` → `has_errors is True` (line 97)
3. **NEW**: `test_fq8_severity_is_error` — drift-prevention test asserting severity=error

## Test Results

```
FQ-8 tests: 11 passed (including new test_fq8_severity_is_error)
Full suite: 7027 passed, 13 skipped, 0 failed
```
