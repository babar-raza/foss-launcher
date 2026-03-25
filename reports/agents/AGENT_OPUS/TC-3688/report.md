# TC-3688 Report — G2 Section-Level Repetition Detection

## Summary
Extended G2 gate with section-level (H2-delimited) Jaccard comparison at
threshold 0.50, severity `warning`. Catches ~6 near-duplicate sections
missed by paragraph-level detection.

## Changes
- `gate_intra_page_repetition.py`: Added `_extract_sections()` helper,
  `_scan_sections()` function, constants `_SECTION_SIMILARITY_THRESHOLD=0.50`,
  `_MIN_SECTION_WORDS=30`, `_MAX_SECTIONS_PER_FILE=30`. New error code
  `G2_SECTION_LEVEL_REPEAT` with severity `warning`.

## Tests
- 9 new tests in `tests/unit/workers/w9/test_g2_section_repetition.py`
  - `TestExtractSections` (4): basic, code fence, H3 not split, empty
  - `TestSectionRepeatDetection` (4): duplicate detected, distinct OK,
    short skipped, severity is warning
  - `TestSectionRepeatIntegration` (1): full gate integration

## Verification
- Full suite: 8617 passed, 0 failed (PYTHONHASHSEED=0)
