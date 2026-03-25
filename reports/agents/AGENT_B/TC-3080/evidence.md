# Evidence — TC-3080: PhaseSelector Self-Derive Validation Summary

## Date: 2026-02-27

## Changes Made

### `src/launch/autopilot/phase_selector.py`

**Lines 204-227** (inserted block):

1. Added `validation_data: Optional[Dict[str, Any]] = None` before W9 checkpoint loop.
2. Added `if ok: validation_data = data` after checkpoint check passes — captures parsed validation report.
3. Added auto-derive block in post-validation section:
   - Runs only when `validation_summary is None and validation_data` is truthy
   - Counts `blocker_count` and `error_count` from `issues[]` using `isinstance(i, dict)` guard
   - If `fixable_count > 0`: sets `validation_summary = {"fixable_count": fixable_count, "blocker_count": blocker_count}`
   - Existing `if validation_summary:` block handles both caller-provided and auto-derived paths

### `tests/unit/autopilot/test_phase_selector.py`

Added helper `_setup_w9_with_issues(run_dir, issues)` and class `TestSelfDerivedValidation` (8 tests).

## Test Run — Target File Only

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/autopilot/test_phase_selector.py -v
```

Result:
```
collected 24 items
tests\unit\autopilot\test_phase_selector.py ........................     [100%]
24 passed, 1 warning in 0.84s
```

All 16 prior tests + 8 new tests = 24 total, 0 failures.

## Test Run — Full Suite

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
```

Result:
```
7163 passed, 13 skipped, 3 xfailed, 9 xpassed, 47 warnings in 193.59s
```

Zero failures. Prior baseline was 7026 passed; net +8 new tests confirmed.

## Backward Compat Verified

`test_explicit_summary_takes_precedence`: empty issues in report + caller passes
`validation_summary={"fixable_count": 1, "blocker_count": 0}` → W10.
The auto-derive block is guarded by `if validation_summary is None`.

## Safety Guards Verified

- `isinstance(i, dict)` guard prevents malformed issue entries from crashing severity counts.
- `validation_data.get("issues", [])` handles missing `issues` key gracefully.
