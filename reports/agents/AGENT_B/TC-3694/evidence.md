# TC-3694 Evidence Report

## Summary

TC-3694 implements three targeted changes to address IT-02 (intra-page claim repetition)
and IT-11 (non-publishable topic selection).

## Changes Made

### Part A: W5 Disjoint Claim Allocation (`multi_pass.py`)
- Added `_partition_claims_across_sections(all_claims, n_sections, max_per_section=5)`:
  round-robin distribution ensuring no claim appears in two sections.
- Modified `_build_evidence_packs()`: when ALL sections have empty `claim_ids`, pre-partition
  page claims before the section loop. Mixed sections (some with IDs) use existing path.

### Part B: G2 Section Severity Upgrade (`gate_intra_page_repetition.py`)
- In `execute_gate()`, after collecting all issues, upgraded `G2_SECTION_LEVEL_REPEAT`
  severity from "warning" → "error" for non-local profiles (ci/prod/pilot).
- Local profile retains "warning" for developer convenience.

### Part C: W4 Topic Admissibility Filter (`worker.py`)
- Added `_STUB_SIGNAL_RE` (word-boundary, case-insensitive): `\b(placeholder|stub|no[_-]op|dummy)\b`
- Added `_filter_inadmissible_pages(page_plan, claims_by_id)`:
  - Signal 1: slug or title matches stub pattern → remove
  - Signal 2: ALL `required_claim_ids` have `visibility: internal` → remove
  - Empty `required_claim_ids` is not filtered by signal 2
- Call site in `execute_ia_planner()` after `_refine_slugs()`.

## Test Results

### New Tests (23 total)
```
tests/unit/workers/w5_section_writer/test_tc3694_section_claim_allocation.py  11 passed
tests/unit/workers/w4_ia_planner/test_tc3694_topic_admissibility.py           12 passed
```

### Updated Tests
- `tests/unit/workers/w9/test_g2_section_repetition.py::test_section_repeat_in_full_gate`:
  Updated assertion from `"warning"` → `"error"` to match TC-3694 severity upgrade.

### Full Suite
```
8724 passed, 13 skipped, 3 xfailed, 47 warnings in 182.61s
```
(+23 tests from 8701 baseline)

## Verification Commands

```bash
PYTHONHASHSEED=0 pytest tests/unit/workers/w5_section_writer/test_tc3694_section_claim_allocation.py -v
PYTHONHASHSEED=0 pytest tests/unit/workers/w4_ia_planner/test_tc3694_topic_admissibility.py -v
PYTHONHASHSEED=0 pytest tests/ 2>&1 | tail -3
# Result: 8724 passed, 13 skipped, 3 xfailed, 0 failed
```
