---
id: CGB-05
title: "Missing test coverage — TC-4034/4037/Wave 4F/4G"
status: Open
priority: Medium
gap: TEST-MISSING
plan: crispy-growing-pebble
waves: [4A, 4C, 4F, 4G]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-05-missing-test-coverage.md
  - tests/unit/workers/test_enforcement.py
  - tests/unit/workers/generate/test_tc4034_competitor_links.py
  - tests/unit/workers/test_route_consistency.py
  - tests/unit/test_finding_classifier.py
  - plans/taskcards/TC-4047_missing-test-coverage.md
---

# CGB-05 — Missing Test Coverage (TC-4034 / TC-4037 / Wave 4F / 4G)

## Gap linkage

**Gap**: TEST-MISSING (MEDIUM)
**Origin**: Self-review of crispy-growing-pebble Waves 4A, 4C, 4F, 4G
**Effect**: Four significant pieces of production logic shipped with zero unit tests:
1. `_strip_competitor_links()` in `worker.py` (TC-4034)
2. `check_route_consistency()` in `route_consistency.py` (TC-4037)
3. `grade_page()` with `editorial_high` path (Wave 4F — `EDITORIAL_CRITICAL_CHECKS`)
4. `evaluate_go_criteria()` with editorial criterion (Wave 4G)

Without tests, regressions will be invisible until content quality degrades.

## Role

Engineering — test suite

## Scope

### Fix (4 test modules)

**A. TC-4034: `_strip_competitor_links()`**
File: `tests/unit/workers/generate/test_tc4034_competitor_links.py` (new file)
- `test_strips_openpyxl_link`: `[openpyxl docs](https://openpyxl.readthedocs.io/...)` → `openpyxl docs`
- `test_strips_pandas_link`: pandas.pydata.org URL → anchor text only
- `test_keeps_aspose_link`: `[Aspose.Cells](https://products.aspose.com/...)` → unchanged
- `test_skips_code_blocks`: link inside ` ``` ` block → not stripped
- `test_multiple_competitors_in_one_section`: all stripped in single pass

**B. TC-4037: `check_route_consistency()`**
File: `tests/unit/workers/test_route_consistency.py` (new file)
- `test_on_topic_page_no_finding`: slug=`how-to-load-spreadsheets`, prose contains "load" → no findings
- `test_off_topic_page_high_finding`: slug=`formula-calculation`, prose about loading files → HIGH
- `test_skip_role_landing`: slug=`products/_index`, page_role=`landing` → no findings (skip)
- `test_stop_words_not_used_as_slug_words`: slug=`how-to-use-cells`, stop words ignored
- `test_short_slug_words_ignored`: slug=`api-for`, "for" ignored (< 4 chars)

**C. Wave 4F: `grade_page()` editorial path**
File: `tests/unit/test_finding_classifier.py` (extend existing)
- `test_grade_editorial_critical_high_returns_D`: finding with check=`route_consistency`, severity=`high` → Grade D
- `test_grade_editorial_critical_claim_coverage_returns_D`: finding check=`claim_coverage`, severity=`high` → Grade D
- `test_grade_editorial_critical_medium_not_D`: editorial check finding with severity=`medium` → not Grade D
- `test_grade_editorial_critical_plus_non_safety_high`: editorial HIGH + regular HIGH → Grade D (not C)

**D. Wave 4G: `evaluate_go_criteria()` editorial criterion**
File: `tests/unit/workers/test_enforcement.py` (extend existing, or new file)
- `test_go_criteria_editorial_rate_below_threshold`: all pages clean → editorial criterion PASS
- `test_go_criteria_editorial_rate_above_threshold`: >15% pages have route_consistency HIGH → criterion FAIL + NO_GO
- `test_go_criteria_fourth_criterion_present`: result always has 4 GoCriteria entries
- `test_go_criteria_editorial_rate_boundary_15pct`: exactly 15% → PASS (threshold is ≤ 15%)

### Allowed paths
- `tests/unit/workers/generate/test_tc4034_competitor_links.py` (new)
- `tests/unit/workers/test_route_consistency.py` (new)
- `tests/unit/test_finding_classifier.py` (extend existing)
- `tests/unit/workers/test_enforcement.py` (extend existing, or new)
- `plans/taskcards/TC-4047_missing-test-coverage.md` (required before coding)
- `plans/healing/CGB-05-missing-test-coverage.md`

### Forbidden
- No changes to `src/launcher/**` — tests only
- Do not modify existing test assertions — only append new test cases

## Pre-requisite

**CGB-01 must be Resolved first** — `check_route_consistency()` wiring affects whether
the integration path can be tested end-to-end. Unit tests for the check function itself
are independent and can proceed immediately.

Create `plans/taskcards/TC-4047_missing-test-coverage.md` with status `In-Progress`
before writing test files (AG-002 applies to test changes under `tests/`? Check CLAUDE.md
— `tests/` is not a protected path, but taskcard documents the work regardless).

## Acceptance checks

- [ ] All 5 TC-4034 tests pass (competitor link stripping)
- [ ] All 5 TC-4037 tests pass (route_consistency check)
- [ ] All 4 Wave 4F tests pass (editorial grading tier)
- [ ] All 4 Wave 4G tests pass (GO criteria 4th criterion)
- [ ] No existing tests broken (PYTHONHASHSEED=0 full suite)
- [ ] `pytest --co` shows new test functions in collection

## Deliverables

1. `tests/unit/workers/generate/test_tc4034_competitor_links.py`
2. `tests/unit/workers/test_route_consistency.py`
3. Extended `tests/unit/test_finding_classifier.py` (4 new test functions)
4. Extended/new `tests/unit/workers/test_enforcement.py` (4 new test functions)
5. Taskcard `plans/taskcards/TC-4047_missing-test-coverage.md` (Done)

## Hard rules

- Taskcard TC-4047 before any test file creation/modification
- Tests must use PYTHONHASHSEED=0 convention
- Tests must be deterministic — no randomness, no I/O
- Import only from `launcher.*` and stdlib — no new test dependencies

## Review dimensions

1. **Coverage**: All 4 logical units now have tests?
2. **Specificity**: Tests target edge cases (skip-role, boundary rate, code blocks)?
3. **Determinism**: All pass under PYTHONHASHSEED=0?
4. **Independence**: Tests don't depend on filesystem or LLM calls?

## Now (runbook)

```
1. Create TC-4047 → In-Progress
2. Create test_tc4034_competitor_links.py (5 tests)
3. Create test_route_consistency.py (5 tests)
4. Extend test_finding_classifier.py (4 tests for Wave 4F)
5. Extend/create test_enforcement.py (4 tests for Wave 4G)
6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ --tb=short -q
7. Mark TC-4047 Done; mark CGB-05 Resolved
```
