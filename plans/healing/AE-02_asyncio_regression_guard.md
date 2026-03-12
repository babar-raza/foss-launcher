---
id: AE-02
title: "Add ruff/pre-commit guard against asyncio.get_event_loop().run_until_complete in tests"
status: Done
priority: Low
owner: "agent"
updated: "2026-03-07"
tags: [healing, asyncio, lint, regression-guard]
depends_on: [AE-01]
allowed_paths:
  - plans/healing/AE-02_asyncio_regression_guard.md
  - pyproject.toml
evidence_required:
  - "ruff check tests/ passes with no asyncio violations"
---

# Taskcard AE-02 — Asyncio Regression Guard

## Gap linkage

- G-AE-02: No regression guard prevents reintroduction of `asyncio.get_event_loop().run_until_complete()`

## Objective

Add a ruff ban rule (or equivalent per-file-ignores / custom rule) that flags `asyncio.get_event_loop()` usage in test files. This prevents future authors from reintroducing the manual event-loop pattern that caused the 34-test batch failure.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix
- Add a ruff `[tool.ruff.lint.per-file-ignores]` or `[tool.ruff.lint.flake8-bandit]` configuration to pyproject.toml that flags `asyncio.get_event_loop()` in `tests/**/*.py`
- If ruff doesn't natively support banning specific function calls, use `[tool.ruff.lint.flake8-tidy-imports.banned-api]` to ban `asyncio.get_event_loop` with a message directing to `@pytest.mark.asyncio` + `await`

### Allowed paths
- `pyproject.toml` — add ruff ban configuration

### Forbidden
- Any other file or path

## Inputs

- Current pyproject.toml with `[tool.ruff]` section
- Ruff docs for `banned-api` feature (ruff >= 0.1)

## Outputs

- Updated pyproject.toml with ban rule for `asyncio.get_event_loop` in test files
- Clear error message directing authors to use `@pytest.mark.asyncio` instead

## Acceptance checks

- **CLI**: `ruff check tests/` → no violations (clean)
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` → 1692 passed (no regressions)
- **Config respected end-to-end**: Creating a test file with `asyncio.get_event_loop()` triggers a lint error
- **No mock data in production paths**: N/A
- **Message clarity**: The lint error message says "Use @pytest.mark.asyncio + await instead of asyncio.get_event_loop().run_until_complete()"

## Deliverables

- Updated pyproject.toml with ruff ban configuration
- No new test files needed — the lint rule IS the guard

## Hard rules

- No new deps without justification (ruff is already a dev dep)
- Keep code/docs/tests in sync
- The ban MUST only apply to test files, not production code (production code may legitimately use asyncio.get_event_loop())

## Review dimensions — what 5/5 looks like

| Dimension | 5/5 criteria |
|-----------|-------------|
| Robustness | Any reintroduction of the old pattern is caught at lint time, before CI |
| Minimality | Single config block addition, no new files |
| Correctness | Only bans in tests/**, not src/** |
| Maintainability | Ban message is self-documenting |
| Integration fit | Uses existing ruff toolchain, no new deps |

## Now (runbook)

```bash
# 1. Research ruff banned-api syntax
# ruff docs: https://docs.astral.sh/ruff/settings/#lint_flake8-tidy-imports_banned-api
# 2. Add to pyproject.toml:
# [tool.ruff.lint.flake8-tidy-imports.banned-api]
# "asyncio.get_event_loop".msg = "Use @pytest.mark.asyncio + await instead of manual event loop management"
# 3. Verify no existing violations
ruff check tests/
# 4. Verify ban fires on synthetic violation
echo 'import asyncio; asyncio.get_event_loop()' > /tmp/test_dummy.py
ruff check /tmp/test_dummy.py  # should flag TID251
# 5. Full test suite still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
