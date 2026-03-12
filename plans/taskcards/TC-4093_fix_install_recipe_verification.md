---
id: TC-4093
title: "Fix install recipe verification to use canonical_import not runtime_import"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [understand, install-recipe, python]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4093_fix_install_recipe_verification.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4093/evidence.md
evidence_required:
  - reports/TC-4093/evidence.md
---

# Taskcard TC-4093 — Fix install recipe verification to use canonical_import not runtime_import

## Objective

The Python install recipe verification code incorrectly uses `runtime_import` (a namespace package like `aspose.cells` that requires extra runtime dependencies) instead of `canonical_import` (the pip-installable package like `aspose_cells_foss`). This causes generated verification code to fail when the runtime is not installed separately. Fix the verification code to use `canonical_import`, falling back to `family` if no canonical import is set.

## Required spec references

- `specs/worker_understand.md` (Section: install recipe extraction, verification code generation)

## Scope

### In scope
- `_deterministic.py` `extract_install_recipe` function: change verification code to use `canonical_import` not `runtime_import`
- 3 unit tests covering canonical_import path, family fallback, and empty-when-no-pkg-info
- Evidence file at `reports/TC-4093/evidence.md`

### Out of scope
- Node.js, Java, .NET, Go install recipe paths — those are separate and correct
- Changes to `runtime_import` model field definition
- Changes to `InstallRecipe` model schema

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` (lines 855-857)
- `tests/unit/workers/understand/test_extract.py` (existing test file to extend)

## Outputs

- Modified `_deterministic.py` with corrected verification code
- 3 new test methods in `TestTC4093InstallRecipeVerification` class
- `reports/TC-4093/evidence.md` with test run output

## Allowed paths

- plans/taskcards/TC-4093_fix_install_recipe_verification.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4093/evidence.md

### Allowed paths rationale

- `_deterministic.py`: root-cause fix location for verification code bug
- `test_extract.py`: existing test file, TC-4093 tests go here
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Edit _deterministic.py

Replace lines 855-857 in `extract_install_recipe`:

```python
# TC-4093: Use canonical_import (pip-installable package) for verification,
# not runtime_import (namespace that may require extra runtime deps)
_verify_pkg = product.canonical_import or product.family
verification = (
    f"import {_verify_pkg}\n"
    f"print('Installation successful')"
) if _verify_pkg else ""
```

### Step 2: Add tests to test_extract.py

Add class `TestTC4093InstallRecipeVerification` with 3 test methods:
1. `test_python_verification_uses_canonical_import`
2. `test_python_verification_fallback_to_family_when_no_canonical`
3. `test_python_verification_empty_when_no_pkg_info`

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -q -k "TC4093"
```

### Step 4: Capture evidence

Save test output to `reports/TC-4093/evidence.md`.

## Failure modes

### Failure mode 1: runtime_import attribute missing

**Detection**: `AttributeError: 'ProductIdentity' object has no attribute 'runtime_import'`
**Resolution**: Use `getattr(product, "runtime_import", "")` — already used in old code; new code doesn't use it at all so this is not a risk
**Gate**: Unit test will catch this

### Failure mode 2: canonical_import is None (not empty string)

**Detection**: `f"import {None}"` produces invalid verification code
**Resolution**: `product.canonical_import or product.family` handles None correctly — falsy check covers both `None` and `""`
**Gate**: `test_python_verification_fallback_to_family_when_no_canonical` covers this

### Failure mode 3: Both canonical_import and family are empty

**Detection**: verification would be set to `"import \nprint(...)"` with empty import
**Resolution**: Outer `if _verify_pkg else ""` guard ensures empty string when no package info
**Gate**: `test_python_verification_empty_when_no_pkg_info` covers this

## Task-specific review checklist

1. [ ] Verification code uses `canonical_import` not `runtime_import`
2. [ ] Fallback to `family` when `canonical_import` is empty/None
3. [ ] Empty string returned when both `canonical_import` and `family` are empty
4. [ ] Node.js, Java, .NET, Go paths unchanged
5. [ ] All 3 TC-4093 tests pass
6. [ ] No existing tests broken
7. [ ] Docstrings updated for changed logic block
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_deterministic.py`
2. Modified `tests/unit/workers/understand/test_extract.py` (3 new tests)
3. `reports/TC-4093/evidence.md` with passing test output

## Acceptance checks

1. [ ] Python verification code uses `canonical_import` not `runtime_import`
2. [ ] All 3 TC-4093 tests PASS
3. [ ] No regression to Node/Java/Go verification code paths
4. [ ] Full test suite passes with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: 3/3 PASS
- [ ] Validation: install recipe verification PASS
- [ ] Evidence captured: reports/TC-4093/evidence.md
- [ ] Doc freshness: clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -q -k "TC4093" -v
```

**Expected results**:
- 3 TC-4093 tests pass
- No existing tests broken

## Integration boundary proven

**Upstream**: `ProductIdentity.canonical_import` field (set during understand phase)
**Downstream**: `InstallRecipe.verification_code` consumed by generate worker for install docs
**Contract**: verification_code is a valid Python import statement using the pip-installable package name
