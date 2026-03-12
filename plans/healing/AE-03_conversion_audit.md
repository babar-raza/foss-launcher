---
id: AE-03
title: "Audit all 34 async/await conversions for correctness"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-07"
tags: [healing, asyncio, audit, tests]
depends_on: [AE-01]
allowed_paths:
  - plans/healing/AE-03_conversion_audit.md
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/test_publish.py
evidence_required:
  - "Audit checklist with all 34 methods verified"
  - "PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q → 1692 passed"
---

# Taskcard AE-03 — Conversion Audit

## Gap linkage

- G-AE-04: Transformation was done via script without explicit before/after review of each site

## Objective

Manually audit all 34 converted test methods to verify:
1. Each `async def test_` has exactly one `await` replacing the former `asyncio.get_event_loop().run_until_complete()`
2. No expressions were lost or mangled during multi-line conversion
3. Indentation is correct (especially the `pytest.raises` case)
4. No sync test methods were accidentally made async
5. No async test methods were missed

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix
- Read-then-fix: audit each of the 34 converted methods; fix any misconversions found
- Verify no sync-only test methods were accidentally converted to async
- Verify the multi-line `pytest.raises` case (test_wrong_input_type in TestEvaluateWorker) has correct indentation

### Allowed paths
- `tests/unit/workers/test_evaluate.py` — fix any misconversions
- `tests/unit/workers/test_publish.py` — fix any misconversions

### Forbidden
- Any other file or path

## Inputs

- test_evaluate.py with 28 async test methods
- test_publish.py with 6 async test methods
- Original git history for comparison (`git diff HEAD~1 -- tests/unit/workers/test_evaluate.py tests/unit/workers/test_publish.py`)

## Outputs

- Verified (and potentially corrected) test files
- Audit checklist confirming each method

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` → 1692 passed
- **Tests**: Each of the 34 methods runs individually: `pytest tests/unit/workers/test_evaluate.py::TestClassName::test_method -x` for spot-checks
- **Audit checklist**: All 34 methods checked off
- **No mock data in production paths**: N/A
- **Sync methods untouched**: `grep -c "def test_" tests/unit/workers/test_evaluate.py` matches expected count of sync-only methods (those without asyncio calls)

## Deliverables

- Corrected test files (if any issues found)
- Audit evidence: list of all 34 methods with pass/fail notation

## Hard rules

- Do not change test logic — only fix conversion artifacts (indentation, missing await, etc.)
- No new deps
- Deterministic runs (PYTHONHASHSEED=0)

## Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Every single converted method individually verified |
| Correctness | Zero misconversions remain |
| Minimality | Only fixes actual issues, no gratuitous changes |
| Robustness | Multi-line and edge cases explicitly verified |
| Testability | Individual method runs confirm correctness |

## Now (runbook)

```bash
# 1. Review the diff
git diff HEAD~1 -- tests/unit/workers/test_evaluate.py tests/unit/workers/test_publish.py

# 2. Count async vs sync test methods
grep -c "async def test_" tests/unit/workers/test_evaluate.py   # expect 28
grep -c "    def test_" tests/unit/workers/test_evaluate.py     # count sync methods
grep -c "async def test_" tests/unit/workers/test_publish.py    # expect 6
grep -c "    def test_" tests/unit/workers/test_publish.py      # count sync methods

# 3. Count await statements
grep -c "await " tests/unit/workers/test_evaluate.py   # expect 28
grep -c "await " tests/unit/workers/test_publish.py    # expect 6

# 4. Spot-check the pytest.raises multi-line case
grep -A2 "pytest.raises" tests/unit/workers/test_evaluate.py

# 5. Run individual methods that had multi-line conversions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestEvaluateWorker::test_wrong_input_type -x -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestSelfReview::test_wrong_output_type -x -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
