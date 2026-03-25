# TC-3450 Self-Review — W10 Stale Path Guard

**Taskcard**: TC-3450
**Date**: 2026-02-28
**Agent**: agent_b
**Status at review**: Done

---

## 12-Dimension Review Table

| # | Dimension | Score | Evidence |
|---|-----------|-------|---------|
| 1 | Coverage | 5/5 | 4 new deterministic tests in `TestStalePathGuard`; 1 existing test updated (`test_truly_missing_file_raises_stale_error`); guard covers all branches: missing path, existing path, no location.path, non-dict location |
| 2 | Correctness | 5/5 | Guard fires only when `location.path` is set AND file does not exist; reuses existing `StaleValidationReportError` exception class; `isinstance(dict)` guard prevents AttributeError on malformed issues |
| 3 | Evidence | 5/5 | Implementation confirmed via grep (line numbers captured); test output captured; `test_truly_missing_file_raises_stale_error` behavioural change documented with old vs. new expected behaviour |
| 4 | Test Quality | 5/5 | All 4 tests use `tmp_path` fixture (deterministic, no LLM, no network); positive + negative + edge-case tests present; error message content verified independently in `test_stale_path_error_message_contains_path_and_issue_id` |
| 5 | Maintainability | 5/5 | Guard is 18 lines with a descriptive TC-3450 comment; reuses existing event constant naming convention (`EVENT_FIXER_*`); no new modules or dependencies introduced |
| 6 | Safety | 5/5 | Fail-safe approach: raises exception rather than returning silent `"unfixable"` status; prevents orchestrator from indefinitely cycling on stale issues; exception is caught at orchestrator boundary |
| 7 | Security | 5/5 | Path is sourced from own validation report (not user input); `Path.exists()` does not follow symlinks to untrusted locations; no path traversal risk |
| 8 | Reliability | 4/5 | Single `Path.exists()` call; narrow TOCTOU window (file deleted after guard but before apply_fix would already be caught by apply_fix itself); no race condition introduced beyond pre-existing W10 risks |
| 9 | Observability | 5/5 | `FIXER_STALE_PATH_DETECTED` telemetry event emitted before raise with `issue_id` and `path` payload; error message in exception also contains both fields for triage log inspection |
| 10 | Performance | 5/5 | Single `Path.exists()` syscall per `execute_fixer()` invocation; negligible overhead; no loops, no I/O beyond the stat call |
| 11 | Compatibility | 5/5 | All 26 existing tests in `test_w10_path_normalization.py` continue to pass; no public API changes in `worker.py`; `StaleValidationReportError` is already part of the module's public exception hierarchy |
| 12 | Docs/Specs Fidelity | 5/5 | Aligned with `specs/28` fix loop policy (W10 signals stale state via exception), `specs/21` worker contract (raises on precondition failure), and `specs/11` event standards (emit event before raise) |

**Overall**: 59/60 — Implementation is complete, well-tested, and correctly aligned with spec.

---

## Known Gaps

None identified. The single 4/5 score on Reliability (#8) is a pre-existing limitation of filesystem-based checks (narrow TOCTOU window) that is consistent with all other W10 path operations and is not a regression introduced by this TC.

---

## Conclusion

TC-3450 is complete. The stale path guard is implemented correctly, tested with 4+1 deterministic tests, observable via telemetry, and aligned with the coordination spec. No regressions in the full W10 path normalization test suite (26/26 passing).
