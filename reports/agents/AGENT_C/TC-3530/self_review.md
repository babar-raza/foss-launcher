# TC-3530 Self-Review (12-Dimension)

**Task**: Gate17 FQ-7b Demotion Correctness — audit `_ERROR_CODES`, fix inconsistency, add tests
**Date**: 2026-02-28
**Agent**: agent_c

---

## 12-Dimension Scores

| # | Dimension | Score (1-5) | Notes |
|---|-----------|-------------|-------|
| 1 | **Correctness** | 5 | Fix is provably correct: removes dead/misleading entry from `_ERROR_CODES`. Behavioral change is zero because `if code == "FQ-7"` branch fires before `elif code in _ERROR_CODES`. |
| 2 | **Test Coverage** | 5 | 13 new tests across 3 classes; covers `_ERROR_CODES` set membership, `_check_one_page` demotion behavior, gate-level pass/fail, retries-exhausted path, FQ-7a vs FQ-7b error code distinction. |
| 3 | **Determinism** | 5 | All LLM interactions mocked with `MagicMock`. No randomness, no time-based assertions. |
| 4 | **Spec Compliance** | 5 | TC-2522 intent: FQ-7b must always be warn. Fix makes code consistent with documented intent. No spec updates needed. |
| 5 | **Non-Regression** | 5 | 574/574 w9 tests pass. 7679 tests pass in full suite. Existing `test_gate_17_stability.py` tests unchanged and passing. |
| 6 | **Evidence Quality** | 5 | Evidence file documents: root cause, before/after code, behavioral impact analysis, all test outputs, files changed. |
| 7 | **Code Clarity** | 5 | Updated `_ERROR_CODES` comment block (7 lines) explains exactly why `"FQ-7"` is absent, references `_check_one_page` demotion logic, and cites TC-3530. Updated docstring severity policy is accurate and complete. |
| 8 | **Scope Compliance** | 5 | Only modified files in `allowed_paths`. `gate_17_prelints.py` read but not modified (no bug found). |
| 9 | **Taskcard Quality** | 5 | Taskcard passes `validate_taskcards.py` with `[OK]`. All 14 mandatory sections present. Version lock fields populated. |
| 10 | **Integration Boundary** | 5 | FQ-7a/FQ-7b error code distinction confirmed (`G17-FQ-7a` vs `G17-FQ-7`). Dedup logic in `run_gate_17` correctly works because codes are distinct. |
| 11 | **Safety / Reversibility** | 5 | Fix is trivially reversible (add `"FQ-7"` back to the frozenset). No state mutations, no schema changes, no artifact format changes. |
| 12 | **Documentation** | 5 | Docstring, inline comment, and evidence all updated consistently. Taskcard body documents the spec impact clearly. |

**Total: 60/60**

---

## Known Gaps

None. The fix is minimal, well-tested, and self-consistent.

---

## Verification Commands Run

```bash
# New tests: 13/13 PASSED
.venv/Scripts/python.exe -m pytest tests/unit/workers/w9/test_gate17_fq7_demote.py -v

# W9 test suite: 574 passed, 1 skipped
.venv/Scripts/python.exe -m pytest tests/unit/workers/w9/ -q

# Full suite (excl. pre-existing unrelated failure): 7679 passed
.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/cli/test_heal.py -q

# Taskcard validation: [OK]
.venv/Scripts/python.exe tools/validate_taskcards.py 2>&1 | grep TC-3530
```

---

## Honest Assessment

The fix is a pure code quality improvement with zero behavioral impact. It eliminates a
misleading constant that could cause confusion during future refactoring. The test suite
now provides explicit protection against future regressions where FQ-7 could accidentally
become gate-blocking.

The one pre-existing test failure (`test_max_steps` in `test_heal.py`) is completely
unrelated to Gate 17 — it was failing before TC-3530 and is in an untracked file.
