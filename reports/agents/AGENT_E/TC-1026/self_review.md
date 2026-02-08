# TC-1026 Self-Review: Remove All W2 Extraction Limits

**Agent:** Agent-E
**Date:** 2026-02-07
**Score:** 5/5

## Checklist

| Criterion | Pass | Notes |
|-----------|------|-------|
| Objective met | Yes | All four limits removed |
| No regressions | Yes | 2194 passed, 12 skipped, 0 failed (1 deselected is pre-existing W1 issue from another agent) |
| Tests updated | Yes | 3 existing tests updated, 5 new tests added |
| Telemetry added | Yes | `claims_extracted_count`, `docs_processed_count`, `examples_processed_count` |
| Taskcard created | Yes | `plans/taskcards/TC-1026_remove_w2_extraction_limits.md` |
| Evidence written | Yes | This file + `evidence.md` |
| Allowed paths respected | Yes | Only touched allowed_paths files |

## Changes Summary

### extract_claims.py (3 changes)
1. **Line 370**: Changed `len(sentence.split()) >= 4` to `>= 1` -- removes 4-word minimum
2. **Lines 372-385**: Converted keyword marker from gate to scoring boost (`keyword_boost` metadata field)
3. **Line 419**: Removed `doc_files[:10]` slice -- processes ALL discovered documents
4. **Logger**: Added `claims_extracted_count` and `docs_processed_count` telemetry

### worker.py (2 changes)
1. **Line 314**: Removed `example_files[:10]` slice -- processes ALL discovered examples
2. **Logger**: Added `examples_processed_count` telemetry

### test_tc_411_extract_claims.py (8 changes)
1. Updated `test_extract_candidate_statements_accepts_short_sentences` (renamed from filters variant)
2. Updated `test_extract_candidate_statements_includes_line_numbers` to expect all 3 sentences
3. Added `TestTC1026NoExtractionLimits` class with 5 new tests:
   - `test_single_word_sentences_are_candidates`
   - `test_keyword_boost_present_on_candidates`
   - `test_no_keyword_sentences_still_extracted`
   - `test_no_doc_count_limit_in_llm_extraction`
   - `test_no_example_count_limit_in_assembly`

## Risk Assessment

- **Low risk**: Changes are additive (more candidates extracted, more examples included). No functional paths removed.
- **Backward compatibility**: The `keyword_boost` field is new metadata on candidates; downstream consumers that do not use it are unaffected.
- **Pre-existing failure**: `test_tc_400_repo_scout.py::TestRepoScoutIntegration::test_no_docs_no_examples` fails due to W1 discover_docs.py changes from another agent (TC-1022). Not related to TC-1026.
