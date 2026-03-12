---
id: AE-01
title: "Switch asyncio_mode to strict + add explicit @pytest.mark.asyncio decorators"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-07"
tags: [healing, asyncio, tests, pytest]
depends_on: []
allowed_paths:
  - plans/healing/AE-01_strict_asyncio_mode.md
  - pyproject.toml
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/test_publish.py
evidence_required:
  - "PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q → 1692 passed, 0 failed"
---

# Taskcard AE-01 — Switch asyncio_mode to strict + explicit decorators

## Gap linkage

- G-AE-01: `asyncio_mode = "auto"` is a footgun for async helper functions
- G-AE-03: No comment explaining the pyproject.toml setting

## Objective

Change `asyncio_mode` from `"auto"` to `"strict"` in pyproject.toml and add explicit `@pytest.mark.asyncio` decorators to all 34 converted async test methods in test_evaluate.py and test_publish.py. This matches the pattern already used by test_generate.py, test_intake.py, and test_understand.py, and prevents accidental auto-detection of non-test async functions.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix
- Change `asyncio_mode = "auto"` to `asyncio_mode = "strict"` in pyproject.toml
- Add inline comment explaining the setting
- Add `@pytest.mark.asyncio` decorator before each of the 28 `async def test_` methods in test_evaluate.py
- Add `@pytest.mark.asyncio` decorator before each of the 6 `async def test_` methods in test_publish.py

### Allowed paths
- `pyproject.toml` — change asyncio_mode value + add comment
- `tests/unit/workers/test_evaluate.py` — add 28 `@pytest.mark.asyncio` decorators
- `tests/unit/workers/test_publish.py` — add 6 `@pytest.mark.asyncio` decorators

### Forbidden
- Any other file or path

## Inputs

- Current pyproject.toml with `asyncio_mode = "auto"`
- test_evaluate.py with 28 `async def test_` methods (no decorators)
- test_publish.py with 6 `async def test_` methods (no decorators)
- Pattern reference: test_generate.py uses `@pytest.mark.asyncio()` (with parens)

## Outputs

- pyproject.toml with `asyncio_mode = "strict"` and inline comment
- test_evaluate.py with `@pytest.mark.asyncio` on all 28 async test methods
- test_publish.py with `@pytest.mark.asyncio` on all 6 async test methods

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` → 1692 passed, 0 failed
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py tests/unit/workers/test_publish.py -x -q` → 133 passed, 0 failed (batch mode)
- **Config respected end-to-end**: `grep asyncio_mode pyproject.toml` shows `"strict"`
- **No mock data in production paths**: N/A (test-only change)
- **Pattern consistency**: `grep -c "pytest.mark.asyncio" tests/unit/workers/test_evaluate.py` → 28; same for test_publish.py → 6
- **No auto-detection surprises**: Adding a bare `async def helper()` to a test file does NOT cause pytest to treat it as a test

## Deliverables

- Full file replacements for pyproject.toml, test_evaluate.py, test_publish.py
- No new tests needed — existing 34 tests ARE the coverage

## Hard rules

- Keep public signatures unchanged
- No network in offline tests
- No new deps
- Deterministic runs (PYTHONHASHSEED=0)
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All 34 methods decorated, no orphan async defs |
| Consistency | Matches test_generate/test_intake/test_understand pattern exactly |
| Production grading | Linter-clean, CI-ready |
| Correctness | 1692/1692 tests pass in batch |
| Minimality | Only decorator additions + one config line change |
| Robustness | `strict` mode prevents future auto-detection surprises |
| Maintainability | Comment explains the setting; pattern is self-documenting |

## Now (runbook)

```bash
# 1. Change asyncio_mode in pyproject.toml
# Edit: asyncio_mode = "auto" → asyncio_mode = "strict"  # require explicit @pytest.mark.asyncio
# 2. Add @pytest.mark.asyncio before each async def test_ in test_evaluate.py (28 sites)
# 3. Add @pytest.mark.asyncio before each async def test_ in test_publish.py (6 sites)
# 4. Verify pattern count
grep -c "pytest.mark.asyncio" tests/unit/workers/test_evaluate.py  # expect 28
grep -c "pytest.mark.asyncio" tests/unit/workers/test_publish.py   # expect 6
# 5. Run batch test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py tests/unit/workers/test_publish.py -x -q
# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 7. Verify strict mode blocks bare async helpers (manual spot-check)
```
