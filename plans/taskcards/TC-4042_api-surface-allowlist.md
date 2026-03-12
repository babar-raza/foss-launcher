---
id: TC-4042
title: "API surface allowlist-first: fix inverted _is_internal_class logic"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [understand, api_surface, allowlist, api_consistency, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4042_api-surface-allowlist.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - tests/unit/workers/understand/extract/test_api_surface.py
evidence_required:
  - reports/TC-4042/evidence.md
---

# Taskcard TC-4042 — API surface allowlist-first: fix inverted _is_internal_class logic

## Objective

Fix inverted logic in `_is_internal_class()` so that when an `export_allowlist` is
present (e.g., from `__init__.__all__`), it is trusted exclusively as the authority on
public/private classes. The current code checks hardcoded Aspose-specific markers BEFORE
the allowlist, meaning a class explicitly exported in `__all__` can still be incorrectly
marked as internal. This directly causes `api_consistency HIGH` findings (wrong API surface
→ LLM references non-existent or filtered-out classes).

## Required spec references

- `specs/worker_understand.md` (API surface extraction)

## Scope

### In scope
- `_api_surface.py`: fix `_is_internal_class()` to check `export_allowlist` first

### Out of scope
- TypeScript import normalization (already handled by tree-sitter workaround in TC-3901)
- `_INTERNAL_CLASS_MARKERS` content (keep as fallback, not as primary)

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` (lines 35-48: `_is_internal_class()`)

## Outputs

- Fixed `_is_internal_class()`: allowlist-first, markers as fallback only
- Passing tests confirming a class in `export_allowlist` is NOT filtered even if name contains a marker

## Allowed paths

- `plans/taskcards/TC-4042_api-surface-allowlist.md`
- `src/launcher/workers/understand/extract/_api_surface.py`
- `tests/unit/workers/understand/extract/test_api_surface.py` (if it exists; create if not)

### Allowed paths rationale
Single-function fix in the API surface extraction logic.

## Implementation steps

### Step 1: Verify current state

Read `src/launcher/workers/understand/extract/_api_surface.py` lines 35-48.
Confirm the markers loop runs BEFORE the allowlist check.

### Step 2: Fix _is_internal_class()

Change the function so allowlist is checked FIRST:

```python
def _is_internal_class(cls_name: str, export_allowlist: frozenset[str] | None = None) -> bool:
    """Check if a class is internal/private.

    When export_allowlist is present (from __all__), it is the authoritative
    source: a class not in the allowlist is internal, regardless of name markers.
    Marker heuristics are used only as a fallback when no allowlist is available.
    """
    if export_allowlist:
        return cls_name not in export_allowlist
    for marker in _INTERNAL_CLASS_MARKERS:
        if marker in cls_name:
            return True
    return False
```

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q -k "api_surface" --ignore=tests/unit/workers/test_publish.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

## Failure modes

### Failure mode 1: export_allowlist is sometimes frozenset(), not None

**Detection**: All classes filtered as internal even when allowlist exists
**Resolution**: Add `if export_allowlist:` (empty frozenset is falsy in Python) — fall through to markers. Or explicitly check `if export_allowlist is not None`.
**Gate**: Test with empty frozenset input.

### Failure mode 2: Marker check needed even when allowlist present

**Detection**: Known internal implementation class (e.g., FndChunk) appears in API surface
**Resolution**: The allowlist IS authoritative — if a class appears in `__all__`, it's exported by intention. Trust the allowlist. Adjust `__all__` extraction if it includes internals.
**Gate**: If test suite has marker-based assertions, verify they still pass.

### Failure mode 3: call sites pass export_allowlist differently

**Detection**: TypeError or wrong behavior at call sites
**Resolution**: Check all calls to `_is_internal_class()` in `_api_surface.py` to confirm the allowlist is passed correctly.
**Gate**: grep for `_is_internal_class(` to find all call sites.

## Task-specific review checklist

1. [ ] `_is_internal_class()` checks `export_allowlist` BEFORE `_INTERNAL_CLASS_MARKERS`
2. [ ] `if export_allowlist:` guard correctly handles both `None` and empty frozenset
3. [ ] Marker fallback still applies when `export_allowlist` is None
4. [ ] All call sites pass `export_allowlist` correctly (grep confirms)
5. [ ] No regression: existing API surface tests pass
6. [ ] Docstring updated to reflect new behavior order
7. [ ] Spec file: no spec drift
8. [ ] Docs ownership: no trigger
9. [ ] Schema: N/A
10. [ ] No new imports needed
11. [ ] Tests verify allowlist takes priority over markers

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_api_surface.py`
2. `reports/TC-4042/evidence.md`

## Acceptance checks

1. [ ] Full test suite: 0 regressions
2. [ ] `grep -A10 "def _is_internal_class" src/launcher/workers/understand/extract/_api_surface.py` shows allowlist check first
3. [ ] A class in export_allowlist is NOT filtered even if name contains a marker string

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: `reports/TC-4042/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

## Integration boundary proven

**Upstream**: `__init__.__all__` extraction provides `export_allowlist: frozenset[str]`
**Downstream**: `ApiSurface.public_classes` contains correct public class names
**Contract**: Classes in `export_allowlist` are always included in `public_classes`
