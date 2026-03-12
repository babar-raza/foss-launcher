---
id: TC-4079
title: "Fix Python namespace package root detection and runtime_import filter"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase3, understand, python, api_surface]
depends_on: [TC-4076]
allowed_paths:
  - plans/taskcards/TC-4079_runtime_import_filter.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - tests/unit/workers/understand/test_python_hardening.py
evidence_required:
  - reports/TC-4079/evidence.md
---

# Taskcard TC-4079 — Fix Python namespace package root detection and runtime_import filter

## Objective

The import-path filter in `_api_surface.py` rejects Python source files whose computed
import path starts with `runtime_import` (e.g. `aspose.cells`) rather than `canonical_import`
(e.g. `aspose_cells_foss`). This causes 0 classes extracted for repos that use a different
published package name at runtime. Fix: also accept `runtime_import` prefix.

## Required spec references

- `specs/worker_understand.md` (Section: API surface extraction)

## Scope

### In scope
- Add `runtime_import` prefix checking to `_file_passes_filters` in `_api_surface.py`
- Tests verifying that runtime_import prefix is accepted

### Out of scope
- Namespace package descent (already implemented at lines 177-191)

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py`

## Outputs

- Updated `_api_surface.py` with runtime_import filter fix

## Allowed paths

- plans/taskcards/TC-4079_runtime_import_filter.md
- src/launcher/workers/understand/extract/_api_surface.py
- tests/unit/workers/understand/test_python_hardening.py

## Implementation steps

### Step 1: Add runtime_import to filter

In `_extract_api_surface()`, extract `runtime_prefix` from `product.runtime_import`:

```python
runtime_import = getattr(product, "runtime_import", "") or ""
runtime_prefix = runtime_import.split(".")[0] if runtime_import else ""
```

Then in `_file_passes_filters`, add:
```python
or (runtime_prefix and import_path.startswith(runtime_prefix))
or (runtime_import and import_path.startswith(runtime_import))
```

## Failure modes

### Failure mode 1: runtime_import is empty string
**Detection**: `product.runtime_import` is "" — no prefix to add
**Resolution**: Guard with `if runtime_prefix:` check — empty string is falsy
**Gate**: API surface filter

### Failure mode 2: runtime_import matches too broadly
**Detection**: runtime_import prefix like "a" matches unrelated modules
**Resolution**: Only check full `runtime_import` or its first dotted component
**Gate**: API surface filter

### Failure mode 3: Two-pass fallback interaction
**Detection**: Package-root-only fallback makes runtime_import filter irrelevant
**Resolution**: The fix is in the strict pass — fallback is unchanged
**Gate**: API surface filter

## Task-specific review checklist

1. [ ] `_file_passes_filters` accepts files whose import path starts with runtime_prefix
2. [ ] `_file_passes_filters` accepts files whose import path starts with full runtime_import
3. [ ] Guard against empty runtime_import (falsy check)
4. [ ] Logging updated to reflect that runtime_import was used
5. [ ] Two-pass structure preserved (strict then fallback)
6. [ ] No regressions in existing tests
7. [ ] Docstrings updated for changed functions
8. [ ] Spec file confirmed — no spec drift
9. [ ] Schema description fields present

## Deliverables

1. Updated `src/launcher/workers/understand/extract/_api_surface.py`
2. Tests in `tests/unit/workers/understand/test_python_hardening.py`

## Acceptance checks

1. [ ] Test `test_runtime_import_filter_not_canonical_import_filter` passes
2. [ ] All existing `test_extract.py` tests pass
3. [ ] `runtime_prefix` accepted in strict filter pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: extraction_audit shows > 1 public class for aspose namespace repos

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_python_hardening.py -v
```

## Integration boundary proven

**Upstream**: ScoutBundle → repo_dir + canonical_import + runtime_import
**Downstream**: Claims extraction uses public_classes from api_surface
**Contract**: All Python source files reachable under runtime_import prefix pass the filter
