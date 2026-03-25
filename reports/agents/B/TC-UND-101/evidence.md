# Evidence: TC-UND-101

## Changes
- _DTS_PROBE_DIRS: 4 → 8 dirs (added build, out, dist/cjs, dist/esm)
- detect_package_root(): exports["."]["types"/"import"/"require"] parsing added
- _find_dts_root(): exports["."]["types"] checked as Step 1b

## Test Evidence
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -k typescript
Result: 41 passed, 0 failed, 2 xpassed (both previously-xfail TS tests now pass)
Full suite: 4315 passed, 0 failed
