# TC-3580 Evidence — launch validate: Separate Output File

## Summary

Fixed `launch validate` to write `validation_report.site.json` instead of
`validation_report.json`, preventing it from clobbering the W9 41-gate canonical
report that `launch triage` and `launch heal` depend on.

Also added a fallback in `load_validation_report()` so that if the W9 report is
absent (e.g. W9 hasn't run yet), the site report is loaded with a loud warning.

## Changes Made

### `src/launch/validators/cli.py` (line ~268)
- Changed `atomic_write_json(artifacts_dir / "validation_report.json", report)`
  to `atomic_write_json(artifacts_dir / "validation_report.site.json", report)`

### `src/launch/cli/triage.py`
- Added `import logging` + `_logger = logging.getLogger(__name__)`
- Updated `load_validation_report()` to:
  - First try `validation_report.json` (W9 format) — preferred
  - Fallback to `validation_report.site.json` if W9 report absent (logs WARNING)
  - Raise `FileNotFoundError` if neither exists

### `tests/unit/cli/test_triage.py`
- Added `TestValidateOutputFile` class (4 tests):
  - `test_w9_report_preferred_when_both_exist`
  - `test_site_report_fallback_loads_when_w9_absent`
  - `test_site_report_fallback_emits_warning`
  - `test_missing_both_raises_file_not_found`

## Test Results

```
.venv/Scripts/python.exe -m pytest tests/unit/cli/test_triage.py::TestValidateOutputFile -v
4 passed in 0.18s
```

Full suite: **7734 passed, 13 skipped, 3 xfailed, 0 failed** (was 7713).

## Root Cause Fixed

`launch validate` wrote to `artifacts/validation_report.json`, overwriting the
W9 41-gate report. This caused `launch triage` and `launch heal` to see the
13-gate site-level format instead of the full 41-gate format, silently breaking
heal ordering and masking real failures.

Fix: Write to distinct filename `validation_report.site.json`. W9's output path
(`validation_report.json`) is unchanged — it remains the canonical handoff report.
