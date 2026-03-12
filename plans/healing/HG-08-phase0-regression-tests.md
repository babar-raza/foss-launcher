# HG-08 — Phase 0 Regression Tests (5 Patches, 0 Tests Written)

**Status**: Not Started
**Gap linkage**: G8 (Phase 0 produced 0 new regression tests; plan required 5+)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: Medium

## Context

The humming-greeting-kay plan Phase 0 acceptance criteria state:
> "5+ new regression tests (one per patch)"

Five bugs were fixed:
- P1: `_compute_api_surface_coverage` inverted metric
- P2: `m.group(1)` false match in `contradiction.py`
- P3: Negation false-positives in `cross_page_review.py`
- P4: `_page_content_cache` empty for heal-cached pages
- P5: Hardcoded format list in `format_truth.py`

Zero regression tests were written. This means any future regression to these
5 fixed bugs would not be caught by the test suite.

## Scope

### Fix

Write 5 targeted regression tests, one per patch, in the evaluate test file.

### Allowed paths

```
tests/unit/workers/test_evaluate.py
plans/taskcards/TC-4014_phase0_regression_tests.md
```

### Forbidden

`evaluate/worker.py`, `evaluate/checks/contradiction.py`,
`evaluate/cross_page_review.py`, `evaluate/checks/format_truth.py` — read-only.
These bugs are already fixed; tests only verify the fix.

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -k "Phase0" -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```
Zero new failures.

### Tests (all must be in class `TestPhase0Regressions`)

**P1 regression** (`test_coverage_metric_uses_page_content`):
- Mock a page with known class name "Scene" in content
- Verify `_compute_api_surface_coverage` returns > 0 when class name present in content
- Verify returns 0 when content is empty (not when findings are empty)

**P2 regression** (`test_contradiction_capture_group_in_fmt_lookup`):
- Create a claim: "Data can be exported to this format"
- Run contradiction check with format matrix that has no "DATA" format
- Verify NO false-positive finding for "Data"
- Verify WOULD find a contradiction for "OBJ can be exported" when OBJ.can_export=False

**P3 regression** (`test_negation_qualified_phrase_not_flat_negative`):
- Input: "cannot be exported without conversion"
- Verify NOT classified as a flat negative (should be "qualified/unknown")
- Input: "cannot export OBJ format"
- Verify IS classified as a negative (no qualification word)

**P4 regression** (`test_page_content_cache_populated_before_early_return`):
- This tests the heal-cached early return path
- Mock a page that is in the heal cache but also in the file system
- Verify `_page_content_cache` has content for that page after evaluate runs

**P5 regression** (`test_format_truth_uses_dynamic_format_list`):
- Create an ApiSurface with format_matrix containing a non-standard format "STEP"
- Run format_truth check on content mentioning "STEP"
- Verify the check uses the dynamic list (STEP is checked)
- Verify a claim about STEP being supported when STEP.can_import=False is caught

### Config respected end-to-end
- Tests are deterministic (no LLM, no network, no filesystem beyond tmp_path)

### No mock data in production paths
- These are unit tests; mocking is appropriate and required

## Deliverables

1. 5 regression tests in `tests/unit/workers/test_evaluate.py`
   under class `TestPhase0Regressions`
2. `plans/taskcards/TC-4014_phase0_regression_tests.md`

## Hard rules

- 5 tests minimum — one per patch
- Each test must fail before the fix and pass after
  (document in comment which bug it covers)
- No LLM or network calls
- Use real evaluate check functions (not mocks of the functions themselves)

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | Each test independently verifiable; no shared state |
| Correctness | Test would catch a regression to the specific bug |
| Minimality | Only test file added; no production code changed |
| Robustness | Tests handle edge cases (empty content, no format matrix) |
| Consistency | Tests follow existing test_evaluate.py patterns |

## Now (runbook)

```
1. Read tests/unit/workers/test_evaluate.py (existing patterns)
2. Read evaluate/checks/contradiction.py (P2 fix — understand the group(1) check)
3. Read evaluate/cross_page_review.py (P3 fix — negation patterns)
4. Read evaluate/checks/format_truth.py (P5 fix — dynamic format list)
5. Write TestPhase0Regressions class with 5 test methods
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -k "Phase0" -v
7. Run full suite
```
