---
id: GR-00
title: "Gap index: golden regression suite self-review (TC-3876a/b)"
status: Reference
priority: Normal
owner: agent
updated: "2026-03-09"
tags: [golden, regression, gap-index, self-review]
---

# GR-00 — Golden Regression Suite Gap Index

Self-review gaps from TC-3876a (golden_loader infrastructure) and TC-3876b
(check regression suite). All gaps are in scope for the healing TCs below.

## Gap summary

| TC | Gap | Severity | Files |
|----|-----|----------|-------|
| GR-01 | Grade-B parametrize shows [NOTSET] — no grade-B pages in corpus | Medium | tests/golden/test_checks_regression.py |
| GR-02 | pyproject.toml not in TC-3876b allowed_paths (governance breach) | Low | plans/taskcards/TC-3876b_check_regression_suite.md |
| GR-03 | installation.md KNOWN_FAILURES comment misclassifies defect as miscalibration | Low | tests/golden/test_checks_regression.py |
| GR-04 | _CONTENT_QUALITY_CHECKS can silently drift when new checks added | Medium | tests/golden/test_checks_regression.py |
| GR-05 | reports/golden_regression_baseline.md never generated (plan deliverable) | Low | reports/TC-3876b/ |
| GR-06 | Silent deduplication: 22 golden files → ~13 unique (role,variant) entries | High | tests/golden/test_checks_regression.py |
| GR-07 | Pre-existing readability test failure claimed without git verification | Low | N/A (investigation only) |
| GR-08 | Regression suite imports private _run_deterministic_checks (fragile) | Medium | tests/golden/test_checks_regression.py |
| GR-09 | grade_letter with empty string not tested; edge case unverified | Low | tests/shared/test_golden_loader.py |
| GR-10 | test_grade_letter_strips_modifier loops two cases in one test (poor isolation) | Low | tests/shared/test_golden_loader.py |

## Execution order

GR-07 (investigation) → GR-05 (baseline report) first.
GR-01, GR-03, GR-04, GR-06, GR-08 can execute in parallel.
GR-02 (governance retroactive fix) any time.
GR-09, GR-10 (test hygiene) any time.

## Severity guide

- **High**: Causes regression suite to under-cover real pages; blocks accurate
  threshold calibration for TC-3877/3878/3879
- **Medium**: Causes silent false confidence or fragile coupling
- **Low**: Process/documentation gap; no correctness risk
