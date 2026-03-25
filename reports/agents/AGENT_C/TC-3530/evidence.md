# TC-3530 Evidence: Gate17 FQ-7b Demotion Correctness

## Summary

TC-3530 audited `gate_17_formatting_quality.py` for the `_ERROR_CODES` inconsistency and
applied a correctness fix (removed `"FQ-7"` from the set). Comprehensive tests verify FQ-7b
is always demoted to warn and FQ-7a correctly fails the gate.

---

## Bug Found: `"FQ-7"` in `_ERROR_CODES` (misleading/dead entry)

### Root Cause

In `src/launch/workers/w9_validator/gates/gate_17_formatting_quality.py` at line 52, the
original code was:

```python
# Note: FQ-7 from LLM (FQ-7b) is now demoted to warn after retry exhaustion
# and is NOT in this set. Only FQ-7a (deterministic) triggers gate failure.
_ERROR_CODES = frozenset({"FQ-1", "FQ-3", "FQ-4", "FQ-7"})
```

The comment contradicts the code: it says FQ-7 is "NOT in this set" but the code includes `"FQ-7"`.

### Why It Was Dead Code

In `_check_one_page()` at lines 291-306, the FQ-7 demotion logic is:

```python
if code == "FQ-7":
    severity = "warn"
    # FQ-7b does NOT set has_errors
elif code in _ERROR_CODES:
    severity = "error"
    has_errors = True
```

Because the `if code == "FQ-7":` branch fires FIRST, `"FQ-7"` in `_ERROR_CODES` could never
be reached for FQ-7 codes. It was dead code that contradicted the documented intent.

### Risk if Not Fixed

If the `if code == "FQ-7":` block were ever refactored (e.g., removed or reordered), the
presence of `"FQ-7"` in `_ERROR_CODES` would silently make FQ-7b gate-blocking — exactly the
regression TC-2522 was designed to prevent. Removing `"FQ-7"` from the set makes the
code self-consistent with the intent.

---

## Fix Applied

### File: `src/launch/workers/w9_validator/gates/gate_17_formatting_quality.py`

**Change 1: `_ERROR_CODES` set** (line 52, TC-3530)

Before:
```python
_ERROR_CODES = frozenset({"FQ-1", "FQ-3", "FQ-4", "FQ-7"})
```

After:
```python
# Note: "FQ-7" is NOT here. FQ-7b (LLM Phase 2) is always demoted to warn
# by the explicit `if code == "FQ-7"` branch in _check_one_page() -- it must
# NEVER block the gate. FQ-7a (deterministic Phase 1 prelint) is handled by
# run_deterministic_prelints() which returns has_errors=True directly via its
# own _ERROR_CODES set (contains "G17-FQ-7a") -- it does NOT go through this set.
# TC-3530: removed "FQ-7" from this set to eliminate the misleading/dead entry.
_ERROR_CODES = frozenset({"FQ-1", "FQ-3", "FQ-4"})
```

**Change 2: Module docstring severity policy** (lines 10-25)

Before:
```
TC-2522: FQ-7 split into:
  - FQ-7a: Heading hierarchy coherence (deterministic, Phase 1) -- severity=error
  - FQ-7b: Narrative flow (LLM, Phase 2) -- severity=error on first success,
    demoted to severity=warn if retries exhausted

Severity policy:
    error codes  (FQ-1, FQ-3, FQ-4, FQ-7a) -- gate fails
    warn codes   (FQ-2, FQ-5, FQ-6)          -- gate passes, issues recorded
    FQ-7b        -- error on success, demoted to warn after retry exhaustion
```

After:
```
TC-2522: FQ-7 split into:
  - FQ-7a: Heading hierarchy coherence (deterministic, Phase 1) -- severity=error
  - FQ-7b: Narrative flow (LLM, Phase 2) -- ALWAYS severity=warn (never blocks gate)

Severity policy:
    error codes  (FQ-1, FQ-3, FQ-4) -- gate fails (see _ERROR_CODES)
    warn codes   (FQ-2, FQ-5, FQ-6) -- gate passes, issues recorded
    FQ-7a        -- error (deterministic prelint, Phase 1, error_code=G17-FQ-7a) -- gate fails
    FQ-7b        -- ALWAYS warn (LLM Phase 2, never in _ERROR_CODES, see _check_one_page)
```

**Change 3: Inline comment in `_check_one_page`** (line 285)

Before:
```python
# Gate 17 enforces the same severity that the prompt assigned.
# Error-level defects (FQ-1/3/4/7) cause the gate to fail.
```

After:
```python
# Gate 17 enforces the severity that the prompt assigned.
# Error-level defects (FQ-1/3/4) cause the gate to fail.
# FQ-7 (FQ-7b) is always demoted to warn regardless of what the LLM said.
```

---

## Audit: `gate_17_prelints.py`

Read and verified `lint_fq7a_heading_hierarchy()` at line 186-208:
- Emits `error_code: "G17-FQ-7a"` (not `"FQ-7"` or `"G17-FQ-7"`)
- Severity is `"error"` — gate-failing, as required
- FQ-7a and FQ-7b use distinct error codes, so dedup logic works correctly

**No changes needed in `gate_17_prelints.py`.**

---

## Test Results

### New Test File: `tests/unit/workers/w9/test_gate17_fq7_demote.py`

Command:
```
.venv/Scripts/python.exe -m pytest tests/unit/workers/w9/test_gate17_fq7_demote.py -v
```

Output:
```
collected 13 items

tests\unit\workers\w9\test_gate17_fq7_demote.py::TestErrorCodesSet::test_fq7_not_in_error_codes PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestErrorCodesSet::test_fq1_in_error_codes PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestErrorCodesSet::test_fq3_in_error_codes PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestErrorCodesSet::test_fq4_in_error_codes PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestErrorCodesSet::test_error_codes_exact_set PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestCheckOnePageFQ7Demotion::test_fq7_from_llm_always_warn PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestCheckOnePageFQ7Demotion::test_fq7_gate_still_passes_when_only_fq7_issues PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestCheckOnePageFQ7Demotion::test_fq7_with_retries_exhausted_returns_no_errors PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestCheckOnePageFQ7Demotion::test_fq1_from_llm_causes_gate_failure PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestCheckOnePageFQ7Demotion::test_fq7_and_fq1_together_gate_fails_but_fq7_still_warn PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestFQ7aVsFQ7bErrorCodes::test_fq7b_issue_has_g17_fq7_error_code PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestFQ7aVsFQ7bErrorCodes::test_fq7a_from_prelints_has_g17_fq7a_error_code PASSED
tests\unit\workers\w9\test_gate17_fq7_demote.py::TestFQ7aVsFQ7bErrorCodes::test_fq7a_and_fq7b_codes_are_distinct PASSED

13 passed, 1 warning in 1.46s
```

**Result: 13/13 PASSED**

### Full W9 Test Suite

Command:
```
.venv/Scripts/python.exe -m pytest tests/unit/workers/w9/ -q
```

Result: `574 passed, 1 skipped, 16 warnings`

### Full Test Suite (excluding pre-existing unrelated failure)

Command:
```
.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/unit/cli/test_heal.py -q
```

Result: `7679 passed, 13 skipped, 3 xfailed, 47 warnings`

The pre-existing failure in `tests/unit/cli/test_heal.py::TestRunHealLoop::test_max_steps`
is unrelated to Gate 17 (it tests heal loop state machine logic) and was already failing
before TC-3530 changes. It is an untracked file in the working tree.

---

## Behavioral Impact Assessment

The fix has **zero behavioral impact** on gate outcomes:

- Before fix: `_ERROR_CODES` contained `"FQ-7"` but the `if code == "FQ-7"` branch in `_check_one_page()` always fired first, preventing FQ-7 from ever reaching `elif code in _ERROR_CODES`
- After fix: `_ERROR_CODES` does not contain `"FQ-7"`. The `if code == "FQ-7"` branch continues to run identically
- Net behavioral change: zero

The fix is a pure code clarity and safety improvement — it prevents future refactoring regressions.

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w9_validator/gates/gate_17_formatting_quality.py` | Remove `"FQ-7"` from `_ERROR_CODES`, update docstring + inline comment |
| `tests/unit/workers/w9/test_gate17_fq7_demote.py` | NEW — 13 tests in 3 test classes |
| `plans/taskcards/TC-3530_gate17_fq7_demote_bugfix.md` | NEW — taskcard |
| `plans/taskcards/INDEX.md` | Added TC-3530 entry |
| `reports/agents/agent_c/TC-3530/evidence.md` | NEW — this file |
| `reports/agents/agent_c/TC-3530/self_review.md` | NEW — self review |
