# TC-2365 Evidence: W2 source_section on Claims

## Changes Made

### `src/launch/workers/w2_facts_builder/extract_claims.py`
- Added `_build_heading_map(lines)` helper function that maps each line number to
  the slug of the nearest Markdown heading above it (code-block-aware)
- Modified `extract_candidate_statements_from_text()`:
  - Calls `_build_heading_map()` before sentence/bullet extraction loops
  - Adds `'source_section': heading_map.get(start_line, "")` to every candidate dict
  - Updated docstring to document the new field
- Modified `_extract_section_claims()`:
  - Adds `'source_section': section_slug` using slugified `section_heading` argument
- Modified `extract_claims_with_llm()`:
  - Passes `'source_section': candidate.get('source_section', "")` to final claim dict

### `tests/unit/workers/test_tc_411_extract_claims.py`
- Added `_build_heading_map` to imports
- Added `TestTC2365SourceSection` class (5 tests):
  - Sentence under heading → correct source_section
  - Content before heading → empty source_section
  - Bullet under heading → correct source_section
  - claim_id unchanged by source_section addition
  - _build_heading_map basic unit test

## Test Results

```
tests/unit/workers/test_tc_411_extract_claims.py::TestTC2365SourceSection::test_source_section_set_for_sentence_under_heading PASSED
tests/unit/workers/test_tc_411_extract_claims.py::TestTC2365SourceSection::test_source_section_empty_before_any_heading PASSED
tests/unit/workers/test_tc_411_extract_claims.py::TestTC2365SourceSection::test_source_section_set_for_bullet_under_heading PASSED
tests/unit/workers/test_tc_411_extract_claims.py::TestTC2365SourceSection::test_source_section_does_not_affect_claim_id PASSED
tests/unit/workers/test_tc_411_extract_claims.py::TestTC2365SourceSection::test_build_heading_map_basic PASSED
```

Full suite: 4515 passed, 9 skipped, 1 pre-existing failure (NUL device OS artifact)

## Acceptance Criteria Verification

- [x] All existing W2 tests still pass (187 total, all green)
- [x] 5 new tests pass (4 required + 1 bonus for _build_heading_map)
- [x] `source_section` present on all candidate dicts from both code paths
- [x] `claim_id` unchanged (SHA256 inputs: `normalized_text|claim_kind` only, unchanged)
