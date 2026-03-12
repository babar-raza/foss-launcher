---
id: TC-4100
title: "Fix namespace recursion to explore ALL submodules"
status: Done
priority: High
owner: Agent-B
updated: "2026-03-11"
tags: [understand, api-surface, correctness]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4100_namespace_recursion_multisubmodule.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B/TC-4100/evidence.md
evidence_required:
  - reports/agents/B/TC-4100/evidence.md
---

# Taskcard TC-4100 — Fix namespace recursion to explore ALL submodules

## Objective

The namespace recursion loop in `_api_surface.py` (lines 177–191) only explores the FIRST alphabetically-sorted submodule when `_export_allowlist` is a set of submodule names. For a package like `aspose/__init__.py` exporting `{"threed", "cells", "pdf"}`, only `cells/` is explored because `sorted({"threed","cells","pdf"})[0] = "cells"`. Classes in `threed/` and `pdf/` are entirely missed. This fix replaces single-submodule recursion with ALL-submodule union so that every declared submodule is explored.

## Required spec references

- `specs/worker_understand.md` (Section: API surface extraction — namespace packages)
- `specs/system_contract.md` (Section: Worker output contracts)

## Scope

### In scope
- Fix `_extract_api_surface()` recursion in `src/launcher/workers/understand/extract/_api_surface.py`
- Add regression test covering two-submodule namespace package in `tests/unit/workers/understand/test_extract.py`

### Out of scope
- Scout worker logic (file discovery is unaffected)
- Generate or Evaluate worker changes
- Changes to `_is_submodule_only_allowlist()` predicate logic itself

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` (current implementation with single-submodule while loop)
- `tests/unit/workers/understand/test_extract.py` (existing test suite to extend)

## Outputs

- Updated `_api_surface.py` with ALL-submodule union recursion
- New regression test in `test_extract.py` covering multi-submodule namespace packages
- `reports/agents/B/TC-4100/evidence.md` with test run output

## Allowed paths

- plans/taskcards/TC-4100_namespace_recursion_multisubmodule.md
- src/launcher/workers/understand/extract/_api_surface.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/B/TC-4100/evidence.md

### Allowed paths rationale

- `_api_surface.py` is the file containing the defective recursion loop
- `test_extract.py` is the existing extraction test module — regression test added here
- `evidence.md` captures the test run output proving the fix

## Implementation steps

### Step 1: Read and understand the current while loop

Read `src/launcher/workers/understand/extract/_api_surface.py` lines 165–200. Identify the while loop controlled by `_is_submodule_only_allowlist()`. Note that the loop currently picks only `sorted(allowlist)[0]` — the single alphabetically-first submodule — and recurses into it, replacing `allowlist` with the contents of that one submodule's `__init__.py`.

### Step 2: Replace single-submodule recursion with ALL-submodule union

When `_is_submodule_only_allowlist(allowlist)` is True:
1. Iterate over ALL submodules in `sorted(allowlist)`.
2. For each submodule name `sub`, compute `_sub_init = pkg_root / sub / "__init__.py"`.
3. If `_sub_init.exists()`, call `_extract_exported_names(_sub_init)` and union the result into `union_exports`.
4. After iterating all submodules: if `union_exports` is empty OR still entirely submodule dirs (i.e., `_is_submodule_only_allowlist(union_exports)` is True), break to prevent unbounded recursion (depth cap `_depth < 3` also guards this).
5. Otherwise set `allowlist = union_exports` and continue the loop.

### Step 3: Write regression test with two-submodule namespace package

In `tests/unit/workers/understand/test_extract.py`, add a test using `tmp_path`:
- Create `aspose/__init__.py` exporting `{"threed", "cells"}` (i.e., `__all__ = ["threed", "cells"]`)
- Create `aspose/threed/__init__.py` with `class Scene: pass`
- Create `aspose/cells/__init__.py` with `class Workbook: pass`
- Call `_extract_api_surface()` on the `aspose` package root
- Assert that `public_classes` contains both `Scene` AND `Workbook`

Also add a second test that verifies single-submodule behavior still works (original behavior unchanged).

## Failure modes

### Failure mode 1: Recursion depth exceeded

**Detection**: If union of submodule exports is still submodule names, the loop could theoretically run 3 levels deep.
**Resolution**: The depth cap `_depth < 3` is enforced at the top of the while loop — when depth reaches 3, break unconditionally. This prevents unbounded recursion even for deeply nested namespace packages.
**Gate**: `specs/worker_understand.md` — extraction must terminate within bounded time.

### Failure mode 2: Some submodules missing `__init__.py`

**Detection**: `FileNotFoundError` or empty results for one or more submodules.
**Resolution**: Guard each submodule with `if _sub_init.exists()` before calling `_extract_exported_names()`. Skip missing submodules silently; still collect results from present ones.
**Gate**: `specs/system_contract.md` — worker must not raise on partial repo structures.

### Failure mode 3: Circular imports in namespace packages

**Detection**: `_extract_exported_names()` could theoretically follow circular `__all__` references.
**Resolution**: `_extract_exported_names()` uses AST parsing only — no Python imports are executed, so circular import risk is zero. No additional guard needed.
**Gate**: `specs/worker_understand.md` — AST-only extraction guarantee.

## Task-specific review checklist

1. [ ] The while loop correctly iterates ALL submodules in sorted order, not just `[0]`
2. [ ] Missing submodule `__init__.py` files are skipped with `if _sub_init.exists()` guard
3. [ ] Depth cap `_depth < 3` is enforced before the ALL-submodule union logic runs
4. [ ] Union of exports from all submodules is computed before checking `_is_submodule_only_allowlist` again
5. [ ] Regression test with 2-submodule package passes: both `Scene` and `Workbook` in public_classes
6. [ ] Regression test for single-submodule (original behavior) still passes
7. [ ] Docstrings updated for all changed functions in `_api_surface.py`
8. [ ] Spec file `specs/worker_understand.md` reviewed — no spec drift introduced
9. [ ] Schema `"description"` fields present for any new/changed properties (none expected here)
10. [ ] Checked `docs/README.md` ownership map — no guide update required for internal extraction fix
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated (N/A for this TC)

## Deliverables

1. Updated `src/launcher/workers/understand/extract/_api_surface.py` with ALL-submodule union recursion
2. New regression tests in `tests/unit/workers/understand/test_extract.py`
3. `reports/agents/B/TC-4100/evidence.md` with full pytest output showing 0 failures

## Acceptance checks

- [ ] Test passes: namespace package with 2 submodules → both submodules' classes in `public_classes`
- [ ] Test passes: single submodule (original behavior) still works
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v` — 0 failures
- [ ] No regressions in existing `test_extract.py` tests
- [ ] Evidence file exists at `reports/agents/B/TC-4100/evidence.md`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: namespace multi-submodule extraction PASS
- [ ] Evidence captured: `reports/agents/B/TC-4100/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v
```

**Expected results**:
- All pre-existing `test_extract.py` tests PASS
- New multi-submodule test PASS: `public_classes` contains both `Scene` and `Workbook`
- New single-submodule regression test PASS

## Integration boundary proven

**Upstream**: `_extract_exported_names()` provides per-`__init__.py` export sets to the recursion loop
**Downstream**: `_extract_api_surface()` result is consumed by `UnderstandWorker` which writes `api_surface` into `UnderstandingBundle`
**Contract**: `ApiSurface.public_classes` must contain all publicly exported classes across all namespace submodules — verified by new regression tests
