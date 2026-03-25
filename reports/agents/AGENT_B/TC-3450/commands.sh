#!/bin/bash
# TC-3450 — Exact commands run during implementation

# Verification searches (Phase 0)
grep -n "StaleValidationReportError" src/launch/workers/w10_fixer/worker.py
grep -n "FIXER_STALE" src/launch/workers/w10_fixer/worker.py  # was empty before TC-3450
grep -n "execute_fixer\|_normalize_issue_paths" src/launch/workers/w10_fixer/worker.py

# W8 Phase 2 verification
grep -n "delete_file\|content_hash\|_validate_patch_bundle" src/launch/workers/w8_linker_and_patcher/worker.py

# Targeted test run (W10 path normalization)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_path_normalization.py -v
# Result: 26 passed

# Slug cluster test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "slug" --tb=short -p no:warnings 2>/dev/null | tail -3
# Result: 331 passed, 7323 deselected

# Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no -p no:warnings 2>/dev/null | tail -5
# Result: 7638 passed, 13 skipped, 3 xfailed in 240.47s
