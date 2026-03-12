# AQ-05 — Code Quality: Type Annotations, BlockIR Copy, Internal Markers, Import Paths

**Status**: Done — All 5 gaps addressed. GAP-05 (type annotations), GAP-06 (export reachability), GAP-07 (BlockIR model_copy), GAP-09 (import_allowlist[0]), GAP-11 (simplified filter). 2707 suite green.
**Gap linkage**: GAP-05 (type annotations), GAP-06 (internal markers), GAP-07 (BlockIR copy), GAP-09 (synthetic import paths), GAP-11 (duplicate filtering)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

Five medium-severity code quality gaps from the TC-3816/TC-3817 implementation:

1. **GAP-05**: `class_briefs: list | None` bare type annotations in `section_prompt.py`, `worker.py` (2 locations), and `_generate_page`. Should be `list[ClassBrief] | None`.

2. **GAP-06**: `_INTERNAL_CLASS_MARKERS` is hardcoded to Aspose-specific markers (FND, Chunk, Reference32, BinaryReader). Won't filter internal classes for non-Aspose products. Should derive from `__init__.py` export reachability or make configurable.

3. **GAP-07**: `_validate_identifiers` reconstructs `BlockIR` field-by-field (`BlockIR(type=..., content=..., language=..., claim_ids=..., items=..., level=...)`). If `BlockIR` gains a new field, it silently drops. Should use `block.model_copy(update={...})`.

4. **GAP-09**: Synthetic snippets use `{canonical_import}.{ClassName}()` which assumes flat package structure. For packages like `aspose.cells` the correct import may be `aspose.cells.Workbook` not `aspose_cells_foss.Workbook`. Should use the import allowlist to determine the correct pattern.

5. **GAP-11**: API surface filtering happens in BOTH `_extract_api_surface()` (extract.py) AND `_filter_api_surface()` (worker.py). Now that extract has the contamination filter, the generate-side filter should be simplified or removed to avoid confusion.

## Scope

### Fix

Address all 5 gaps in a single focused taskcard since they are all small, non-interacting code quality fixes.

### Allowed paths
- `src/launcher/workers/generate/section_prompt.py`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/understand/test_extract.py`
- `tests/unit/workers/generate/test_method_validation.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` — all pass
- **Tests**: Synthetic snippet for nested-import product uses correct import path
- **Tests**: `_validate_identifiers` preserves new BlockIR fields if added
- **Config respected end-to-end**: Internal class markers work for both Aspose and non-Aspose products
- **No mock data in production paths**: All changes use real model objects

## Deliverables

1. **GAP-05**: Replace `class_briefs: list | None` with `list[ClassBrief] | None` in 4 locations; add import where needed
2. **GAP-06**: Extend `_is_internal_class()` to also check `_build_export_reachability` when available; keep markers as fallback
3. **GAP-07**: Replace manual `BlockIR(...)` construction with `block.model_copy(update={"content": new_content, "items": new_items})`
4. **GAP-09**: In `_generate_synthetic_snippets`, use `import_allowlist[0]` if available, or fall back to `canonical_import`, for the import line
5. **GAP-11**: Simplify `_filter_api_surface()` in worker.py to only do page-level filtering (remove third-party prefix list, since extract now handles it)
6. Tests for each fix

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (seed/stable ordering) where needed
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Maintainability | All type annotations correct; no field-by-field copies; single source of truth for filtering |
| Consistency | Type annotations match codebase convention (`list[X] | None` with proper imports) |
| Robustness | Internal class detection works for any Python product, not just Aspose |
| Production grading | Synthetic snippets produce valid imports for any package structure |
| Minimality | Each fix is surgical — type annotation swap, method call change, import path fix |

## Now (runbook)

```bash
# 1. Fix type annotations (4 locations)
#    section_prompt.py: build_section_prompt signature + _format_api_surface signature
#    worker.py: _generate_page signature + run method

# 2. Fix BlockIR copy in _validate_identifiers
#    Replace BlockIR(...) with block.model_copy(update={"content": new_content, "items": new_items})

# 3. Fix internal class markers
#    Add fallback to _build_export_reachability check when package_root is known

# 4. Fix synthetic import path
#    Use import_allowlist[0] instead of canonical_import for import line

# 5. Simplify _filter_api_surface in worker.py
#    Remove _THIRD_PARTY_PREFIXES list; keep only claim-mention and family-match filtering

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
