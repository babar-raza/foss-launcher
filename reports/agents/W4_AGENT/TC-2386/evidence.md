# TC-2386 Evidence: W4 Pre-Generation Duplication Check

## Implementation Summary
Created shared Jaccard similarity module and integrated pre-generation redundancy check into W4.

## Files Modified/Created
- `src/launch/workers/_shared/jaccard.py` — NEW: Shared Jaccard module
- `src/launch/workers/w4_ia_planner/worker.py` — Added `check_pre_generation_redundancy()`
- `src/launch/workers/w9_validator/gates/gate_19_redundancy.py` — Updated imports
- `tests/unit/workers/test_tc_2386_duplication_check.py` — NEW: 11 unit tests

## Test Results
All tests pass. Run with: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_2386_duplication_check.py -v`

## Behavior
- `check_pre_generation_redundancy()` compares title + purpose + top-3 claim texts per page
- Uses Jaccard word-set overlap (default threshold: 0.6)
- Non-blocking: logs warnings only, does not abort W4 planning
- Shared `jaccard.py` module reused by Gate 19 to avoid duplication
