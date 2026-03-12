# EV-05 — Missing Test Coverage for New Checks

**Status:** Done (pre-existing)
**Gap linkage:** G-EV-09
**Role:** Senior engineer. Drop-in, production-ready.

## Context

Self-review identified several untested code paths in the TC-3777 implementation:

1. **Keyword stuffing detector** (artifacts.py:99-114) — no test exists
2. **Wrong-case product name** (product_names.py:60-65, e.g., "aspose.cells" in prose) — no direct test for detection (only code-block exclusion is tested)
3. **Medium-severity repetition** (repetition.py:96-103, near-duplicate rate 30-50%) — no test covers the medium path; only the >50% high path is tested
4. **product_name threading** through `_run_deterministic_checks` and into `check_product_names` — no integration-level test verifies the full thread from worker.run → _run_deterministic_checks → check_product_names with a real product_name
5. **Existing `_GOOD_CONTENT` fixture** not explicitly validated against all new checks in a single integration assertion

## Scope

### Fix
Add these test cases to `tests/unit/workers/test_evaluate.py`:

1. `TestCheckArtifactsEnhanced.test_keyword_stuffing_detected` — content with >5 product mentions per 100 words
2. `TestCheckArtifactsEnhanced.test_keyword_stuffing_clean_content` — content with normal mention frequency
3. `TestCheckProductNames.test_wrong_case_in_prose` — "aspose.cells" in prose body (not code) triggers finding
4. `TestCheckRepetition.test_medium_severity_near_duplicate` — content with 30-50% near-duplicate rate produces medium finding
5. `TestRunDeterministicChecks.test_new_checks_included` — verify repetition, product_names, semantic_structure appear in check results
6. `TestRunDeterministicChecks.test_good_content_passes_all_new_checks` — _GOOD_CONTENT produces zero high/critical from any of the 11 checks

### Allowed paths
- `tests/unit/workers/test_evaluate.py`

### Forbidden
- Any other file/path (tests only — no production code changes)

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all pass including 6 new tests
- **Tests:**
  - Each new test has a clear positive assertion (not just "no error")
  - Wrong-case test confirms `severity="medium"` for body matches
  - Medium repetition test confirms `severity="medium"` (not "high")
  - Keyword stuffing test confirms `severity="medium"`
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A (test-only change)

## Deliverables

- 6 new test methods added to existing test classes in `test_evaluate.py`
- All existing 78 tests continue to pass
- New test count: ~84 total

## Hard rules

- No production code changes — test-only taskcard
- Tests must be deterministic (PYTHONHASHSEED=0)
- Each test is self-contained (no shared mutable state)
- Test names follow existing `test_<behavior>` convention
- No new deps

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Coverage | Every untested code path from self-review is now covered |
| Correctness | Each test verifies specific severity level and check name, not just "any finding" |
| Testability | Tests are independent and can run in isolation |
| Maintainability | Tests follow existing class structure and naming patterns |
| Minimality | Exactly 6 tests — one per gap; no over-testing |

## Now (runbook)

```bash
# 1. Read current test file for context
cat tests/unit/workers/test_evaluate.py

# 2. Add test_keyword_stuffing_detected to TestCheckArtifactsEnhanced
#    Content: 20x "Aspose.Cells" in 50 words of prose
#    Assert: any finding with "stuffing" in message

# 3. Add test_keyword_stuffing_clean_content to TestCheckArtifactsEnhanced
#    Content: 2x "Aspose.Cells" in 200 words
#    Assert: no stuffing finding

# 4. Add test_wrong_case_in_prose to TestCheckProductNames
#    Content: "aspose.cells" in body prose (no code block)
#    Assert: finding with severity="medium" and "Wrong case" in message

# 5. Add test_medium_severity_near_duplicate to TestCheckRepetition
#    Content: ~35% near-duplicate rate (some similar, some different sentences)
#    Assert: finding with severity="medium"

# 6. Add test_new_checks_included to TestRunDeterministicChecks
#    Content: triggers all 3 new checks
#    Assert: "repetition", "product_names", "semantic_structure" in checks_hit

# 7. Add test_good_content_passes_all_new_checks to TestRunDeterministicChecks
#    Assert: _GOOD_CONTENT produces zero findings from new checks

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
```
