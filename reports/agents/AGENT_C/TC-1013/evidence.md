# TC-1013 Evidence Report: Remove/Configure W2 Evidence Mapping Caps

**Agent:** Agent-C
**Date:** 2026-02-07
**Status:** Complete

## Files Changed

### 1. `src/launch/workers/w2_facts_builder/map_evidence.py`

Four targeted changes to raise evidence caps and lower relevance thresholds:

| Line | Old Value | New Value | Purpose |
|------|-----------|-----------|---------|
| 152 | `max_evidence_per_claim: int = 5` | `max_evidence_per_claim: int = 20` | Raise docs evidence cap 4x |
| 184 | `if relevance_score > 0.2:` | `if relevance_score > 0.05:` | Lower docs threshold for exhaustive ingestion |
| 202 | `max_evidence_per_claim: int = 3` | `max_evidence_per_claim: int = 10` | Raise examples evidence cap 3.3x |
| 234 | `if relevance_score > 0.25:` | `if relevance_score > 0.1:` | Lower examples threshold for exhaustive ingestion |

### 2. `tests/unit/workers/test_tc_412_map_evidence.py`

- **Updated:** Line 285 threshold assertion from `> 0.2` to `> 0.05` to match new docs threshold
- **Added:** New test class `TestTC1013RaisedCapsAndLoweredThresholds` with 6 tests:
  - `test_docs_default_cap_is_20` -- introspects function signature to verify default
  - `test_examples_default_cap_is_10` -- introspects function signature to verify default
  - `test_docs_cap_allows_up_to_20_results` -- creates 25 docs, verifies up to 20 returned (more than old 5)
  - `test_examples_cap_allows_up_to_10_results` -- creates 15 examples, verifies up to 10 returned (more than old 3)
  - `test_lower_docs_threshold_admits_marginal_evidence` -- verifies evidence in 0.05-0.2 range is now included
  - `test_lower_examples_threshold_admits_marginal_evidence` -- verifies evidence in 0.1-0.25 range is now included

### 3. `plans/taskcards/TC-1013_remove_w2_evidence_mapping_caps.md`

- Created with all 14 mandatory sections per taskcard contract
- YAML frontmatter with all required fields

## Files Created

- `plans/taskcards/TC-1013_remove_w2_evidence_mapping_caps.md`
- `reports/agents/agent_c/TC-1013/evidence.md` (this file)
- `reports/agents/agent_c/TC-1013/self_review.md`

## Commands Run

### Targeted test run
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_412_map_evidence.py -v
```
**Result:** 38 passed, 0 failed (1.32s)

### Full test suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```
**Result:** 1916 passed, 12 skipped, 0 failed (91.27s)

## Test Results Summary

- **Total tests:** 1916 passed, 12 skipped
- **TC-412 specific tests:** 38 passed (32 existing + 6 new)
- **No regressions** detected across the full suite

## Deterministic Verification

- Tests run with `PYTHONHASHSEED=0` as required
- The changes preserve deterministic ordering (sort by relevance_score descending)
- No non-deterministic elements introduced (no timestamps, random IDs, etc.)
- The `max_evidence_per_claim` parameter remains configurable -- callers can still override
