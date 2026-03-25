# Self-Review — TC-4265 + TC-4266

## Scoring (13 dimensions)

| # | Dimension | Score (1-5) | Notes |
|---|-----------|:-----------:|-------|
| 1 | Correctness | 5 | syntax_valid set correctly for Python/TS/other; confidence tiering exact |
| 2 | Test coverage | 4 | 8 new tests cover all stated scenarios; edge case (invalid Python at construction) tested via model |
| 3 | Backward compatibility | 5 | Snippet.syntax_valid defaults to None; old bundles unaffected |
| 4 | Spec adherence | 5 | `confidence=0.70` strictly < 0.75; "overview" excluded from _STRUCTURED_SECTION_HEADINGS |
| 5 | Root-cause fix | 5 | Found that claim_source was missing from bullet/table/paragraph dicts — root cause fixed |
| 6 | No patching | 5 | Changes are in correct files at correct locations, not workarounds |
| 7 | Evidence documented | 5 | All findings in evidence.md with data |
| 8 | Pre-existing failures identified | 5 | Scout test failures verified as pre-existing, not introduced |
| 9 | Test update quality | 4 | Updated tests explain TC-4266 intent clearly |
| 10 | Code consistency | 5 | Followed existing patterns in _snippets.py, _deterministic.py, _validation.py |
| 11 | Option B assessment | 5 | Checked Note's deterministic claims, reasoned Option C correctly |
| 12 | Part C decision | 4 | Applied -20 penalty at _score_doc_path level (affects doc context ordering, not direct snippet filter) |
| 13 | Self-review | 4 | Identified that test `test_python_snippet_syntax_invalid_false` uses model directly because extraction filters invalid Python before Snippet construction |

**Average: 4.7 / 5**

## Gaps / Issues

1. **TC-4265 invalid Python test**: Cannot test invalid Python via `_extract_snippets` because the extraction layer already filters them. The test for `syntax_valid=False` uses the model directly. This is architecturally correct (invalid Python never reaches Snippet construction), but the test is less end-to-end than ideal. Mitigation: added `test_python_snippet_syntax_invalid_false` testing the model field directly, and documented the filter behavior.

2. **Part C scope**: The `-20` penalty in `_score_doc_path` affects doc context priority (budget ordering) but NOT snippet extraction order — snippets are extracted from `all_paths = doc_paths + example_paths` without scoring. The penalty reduces how much of `onenote-api.md` gets into LLM context, which is the right approach for claim extraction. Snippet extraction still processes all docs. This is the correct interpretation of "deprioritize" vs "filter."

3. **claim_source missing**: The root cause finding (bullet/table/paragraph claims had no `claim_source` field) was a pre-existing bug that caused all deterministic markdown claims to be classified as `claim_source="llm"` with `confidence=0.75`. Fixed as part of TC-4266 Part A.

## Healing Plan

No blockers found. Minor gap: a future TC could add end-to-end test for syntax_valid=False by exposing a lower-level function that constructs Snippet with invalid code (skipped by this TC per scope constraints).
