---
id: GR-08
title: "Create public test helper for deterministic checks to decouple from private API"
status: Open
priority: Medium
owner: agent
updated: "2026-03-09"
tags: [golden, regression, test-architecture, worker]
depends_on: []
allowed_paths:
  - plans/healing/GR-08-public-deterministic-checks-wrapper.md
  - tests/golden/test_checks_regression.py
  - tests/conftest.py
evidence_required:
  - reports/GR-08/evidence.md
---

# GR-08 — Decouple regression suite from private `_run_deterministic_checks`

## Objective

`test_checks_regression.py` imports `_run_deterministic_checks` (underscore prefix
= private). If this function is renamed, inlined, or split during refactoring of
`worker.py`, the regression suite breaks silently. Create a thin public wrapper
or conftest fixture that insulates the regression suite from the private implementation
detail, making the coupling explicit and easy to maintain.

## Gap source

TC-3876b self-review: testing a private function is architecturally fragile. The
regression suite should interact with the worker through a stable surface.

## Required spec references

- `plans/purrfect-beaming-crown.md` (TC-3876b: imports `_run_deterministic_checks`
  from `launcher.workers.evaluate.worker`)

## Scope

### In scope
- Add a `run_deterministic_checks_for_golden` function to `tests/conftest.py`
  (or a new `tests/golden/helpers.py`) that wraps the private call with a
  stable, documented signature
- Update `test_checks_regression.py` to import from the wrapper
- The wrapper must be clearly documented as a test-internal shim

### Out of scope
- Making `_run_deterministic_checks` public in `worker.py` (src/ change — separate TC)
- Any changes to worker behaviour

## Inputs

- `tests/golden/test_checks_regression.py`
- `src/launcher/workers/evaluate/worker.py` (private function location)

## Outputs

- `tests/conftest.py` OR new `tests/golden/helpers.py` (wrapper function)
- `tests/golden/test_checks_regression.py` (updated import)
- `reports/GR-08/evidence.md`

## Allowed paths

- plans/healing/GR-08-public-deterministic-checks-wrapper.md
- tests/golden/test_checks_regression.py
- tests/conftest.py

### Allowed paths rationale

Test infrastructure change only. `conftest.py` is the standard pytest location
for shared test utilities. No src/ changes.

## Implementation steps

### Step 1: Decide: conftest.py vs helpers.py

Check if `tests/conftest.py` exists and what it contains. If it's small/empty,
add the wrapper there (it will be auto-discovered by pytest). If it's large,
create `tests/golden/helpers.py` instead (requires explicit import).

Prefer `tests/conftest.py` for discoverability.

### Step 2: Add wrapper to tests/conftest.py

```python
# ---------------------------------------------------------------------------
# Golden regression helpers — stable wrappers around private worker internals
# ---------------------------------------------------------------------------

def run_checks_on_golden_page(
    content: str,
    slug: str,
    *,
    page_role: str,
    product_name: str,
    canonical_import: str,
    golden_dir=None,
):
    """Run deterministic content checks on a golden page.

    Thin wrapper around the private `_run_deterministic_checks` function in
    `launcher.workers.evaluate.worker`. This wrapper provides a stable import
    surface for the golden regression suite — if the private function is renamed
    or refactored, only this wrapper needs to be updated.

    Returns a list of Finding objects (same as _run_deterministic_checks).
    """
    from launcher.workers.evaluate.worker import _run_deterministic_checks
    return _run_deterministic_checks(
        content, slug,
        page_role=page_role,
        product_name=product_name,
        canonical_import=canonical_import,
        golden_dir=golden_dir,
    )
```

### Step 3: Update test_checks_regression.py

Replace:
```python
from launcher.workers.evaluate.worker import _run_deterministic_checks
```

With:
```python
from conftest import run_checks_on_golden_page
```

And replace all calls to `_run_deterministic_checks(...)` with
`run_checks_on_golden_page(...)`.

**Note**: If conftest.py is not on the Python path in some pytest configurations,
use a relative import: `from tests.conftest import run_checks_on_golden_page`
or check the conftest discovery rules for the project.

### Step 4: Verify test still runs correctly

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

Expected: same 6 passed / 1 skipped / 3 xfailed as before.

## Failure modes

### Failure mode 1: conftest.py import fails in test_checks_regression.py

**Detection**: `ModuleNotFoundError: No module named 'conftest'`
**Resolution**: Use `from tests.conftest import run_checks_on_golden_page` with
the package-qualified path; or use a pytest fixture instead of a plain function.
**Gate**: Test collection succeeds without ImportError

### Failure mode 2: conftest.py already has functions that conflict

**Detection**: Existing `run_checks_on_golden_page` or similar function
**Resolution**: Use a different name or add to existing helper module
**Gate**: `grep "run_checks_on_golden_page\|run_deterministic" tests/conftest.py`
before adding

### Failure mode 3: Private function renamed in worker.py during refactoring

**Detection**: `ImportError: cannot import name '_run_deterministic_checks'`
**Resolution**: This is EXACTLY what this wrapper prevents from cascading.
Update ONLY the wrapper — no change to test_checks_regression.py needed.
**Gate**: One-place update is the acceptance criterion

## Task-specific review checklist

1. [ ] Wrapper function in `tests/conftest.py` (or `tests/golden/helpers.py`)
2. [ ] Wrapper has docstring explaining why it exists (stable surface over private API)
3. [ ] `test_checks_regression.py` imports from wrapper, not directly from worker
4. [ ] No `_run_deterministic_checks` import in `test_checks_regression.py`
5. [ ] Test results unchanged after import switch (same pass/skip/xfail counts)
6. [ ] Wrapper itself is not a pytest fixture (plain function — called directly)
7. [ ] Spec file: no worker behavior change
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/conftest.py` (wrapper function added)
2. `tests/golden/test_checks_regression.py` (import updated)
3. `reports/GR-08/evidence.md`

## Acceptance checks

1. [ ] `grep "_run_deterministic_checks" tests/golden/test_checks_regression.py` returns no results
2. [ ] `pytest tests/golden/ -m golden -v` shows same results as before GR-08
3. [ ] Wrapper function has docstring explaining the stable-surface purpose

## Self-review

### Verification results
- [ ] grep confirms no direct private import
- [ ] Tests: same counts as baseline
- [ ] Evidence captured: reports/GR-08/evidence.md

## E2E verification

```bash
grep "_run_deterministic_checks" tests/golden/test_checks_regression.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

**Expected results**:
- `grep` returns no results (private import removed)
- Test results: 6 passed / 1 skipped / 3 xfailed (or adjusted after GR-01)

## Integration boundary proven

**Upstream**: `_run_deterministic_checks` in `worker.py` (private implementation)
**Downstream**: `test_checks_regression.py` (golden regression suite)
**Contract**: `run_checks_on_golden_page(content, slug, *, page_role, product_name, canonical_import, golden_dir)` is the stable test-facing API
