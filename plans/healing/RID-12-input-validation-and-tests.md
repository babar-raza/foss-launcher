# RID-12: Input Validation + Edge-Case Test Coverage

## Status: Done

## Gap Linkage
- G-RV3-03: Empty/whitespace family or platform produces malformed IDs
- G-RV3-04: Missing edge-case tests for empty inputs, max-length slugs, collision, special-char-only slugs

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. **Input validation in `generate_run_id()`**: Raise `ValueError` if `family` or
   `platform` is empty, whitespace-only, or sanitizes to an empty string. Check
   *after* sanitization — `_sanitize_slug("---")` returns `""` which must be caught.

2. **Input validation in `_sanitize_slug()`**: If the result after sanitization is
   empty, raise `ValueError` with a message identifying which input was invalid.

3. **Add edge-case tests** to `tests/unit/util/test_run_id.py`:
   - `test_empty_family_raises`: `generate_run_id("", "python")` → `ValueError`
   - `test_empty_platform_raises`: `generate_run_id("cells", "")` → `ValueError`
   - `test_whitespace_only_raises`: `generate_run_id("  ", "python")` → `ValueError`
   - `test_special_chars_only_raises`: `generate_run_id("---", "python")` → `ValueError`
   - `test_max_length_slug_truncated`: family with 30+ chars produces slug ≤16 chars
   - `test_slug_all_digits`: `_sanitize_slug("12345")` → `"12345"` (valid)
   - `test_slug_mixed_special`: `_sanitize_slug("foo.bar_baz")` → `"foo-bar-baz"`

### Allowed paths
- `src/launcher/util/run_id.py`
- `tests/unit/util/test_run_id.py`

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `python -c "from launcher.util.run_id import generate_run_id; generate_run_id('', 'python')"` raises `ValueError`
- `python -c "from launcher.util.run_id import generate_run_id; generate_run_id('---', 'python')"` raises `ValueError`

### Tests
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py -v` — all pass
- ≥7 new test functions covering all edge cases listed above
- Happy-path tests from previous iteration still pass

### Config respected end-to-end
- All pilot configs have non-empty family/platform, so validation never fires in normal use

### No mock data in production paths
- Validation logic uses no hardcoded values

## Deliverables
- Updated `src/launcher/util/run_id.py` with input validation
- Updated `tests/unit/util/test_run_id.py` with ≥7 new edge-case tests

## Hard Rules
- Keep public signatures unchanged: `generate_run_id(family, platform)`, `_sanitize_slug(value, max_len)`
- Raise `ValueError` (not `SystemExit` or custom exception) — callers already expect this
- No network in offline tests
- Deterministic via `PYTHONHASHSEED=0`
- No new deps
- Code/docs/tests in sync

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All edge cases listed above have both validation and tests |
| Consistency | Same `ValueError` pattern used in both `_sanitize_slug` and `generate_run_id` |
| Production grading | Malformed IDs impossible — caught at generation time, not at mkdir |
| Correctness & spec alignment | Empty/special-only inputs rejected; valid inputs pass through unchanged |
| Scope adherence | Only 2 files touched |
| Testability | Each edge case is an independent test with clear assert |
| Robustness | Post-sanitization check catches inputs that *look* valid but sanitize to empty |
| Minimality | ~5 lines of validation + ~30 lines of tests |

## Now (Runbook)

```bash
# 1. Add validation to _sanitize_slug — raise ValueError if result is empty
# 2. Add validation to generate_run_id — raise ValueError if family/platform empty
# 3. Add 7+ edge-case tests
# 4. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py -v
# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
