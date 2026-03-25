# TC-2892 Self-Review: FQ-8 Bake-in + Severity Promotion

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Coverage | 5/5 | All 3 pilots run, 93 markdown files scanned, 3 evidence files |
| 2 | Correctness | 5/5 | 0 FQ-8 false positives across all pilots; severity promotion correct |
| 3 | Evidence | 5/5 | 3 bake-in evidence files, validation_report.json cited per pilot |
| 4 | Test Quality | 5/5 | 11 FQ-8 tests pass; new drift-prevention test added; full suite 7027/0 |
| 5 | Maintainability | 5/5 | Minimal changes: 3 edits in prelints.py, 3 edits in test file |
| 6 | Safety | 5/5 | Promotion gated on evidence; W10 auto-fix still catches FQ-8 if it fires |
| 7 | Security | 5/5 | No security-relevant changes |
| 8 | Reliability | 5/5 | FQ-8 is deterministic (no LLM), idempotent merger as fallback |
| 9 | Observability | 5/5 | Gate findings logged to validation_report.json with error_code/location |
| 10 | Performance | 5/5 | No performance impact; prelint is O(n) line scan |
| 11 | Compatibility | 5/5 | No API changes; W10 handler unchanged; gate wiring unchanged |
| 12 | Docs/Specs Fidelity | 5/5 | Docstring updated; evidence files follow repo convention |

## What Was Checked
- [x] 3 pilot runs with 0 FQ-8 hits each
- [x] Manual scan of 93 final-output markdown files: 0 adjacent same-language fences
- [x] Severity changed from "warn" to "error" in lint function
- [x] G17-FQ-8 added to _ERROR_CODES frozenset (makes has_errors=True)
- [x] Test assertions updated to match new severity
- [x] New test_fq8_severity_is_error prevents silent drift back to warn
- [x] Full test suite: 7027 passed, 0 failed

## Known Gaps
(none)
