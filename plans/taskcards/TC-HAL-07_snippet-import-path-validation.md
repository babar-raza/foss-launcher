---
id: TC-HAL-07
title: "Import path validation on extracted snippets"
status: Done
priority: Medium
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "snippets"]
depends_on: ["TC-HAL-06"]
allowed_paths:
  - plans/taskcards/TC-HAL-07_snippet-import-path-validation.md
  - src/launcher/workers/understand/extract/_snippets.py
  - tests/unit/workers/understand/test_snippet_claim_extraction.py
evidence_required:
  - reports/TC-HAL-07/evidence.md
---

# Taskcard TC-HAL-07 — Import path validation on extracted snippets

## Objective
After snippet extraction, validate each snippet's import lines against `api_surface.import_allowlist`. Snippets with imports not in the allowlist are flagged as invalid and filtered before passing to downstream phases. This prevents `from aspose.threed import Node` (wrong import path) from propagating into generated content.

## Required spec references
- `specs/worker_understand.md` (Section: Phase B.5 Snippet extraction)

## Scope
### In scope
- After `_extract_snippets()`, scan each Python snippet for import lines
- Check imports against `api_surface.import_allowlist`
- Add `source_type = "invalid_import"` literal to `Snippet.source_type` OR filter invalid snippets before return
- Add `invalid_import_snippet_count` metric to audit

### Out of scope
- Fixing the import path itself (snippets are extracted as-is from source)
- Non-Python snippets (skip import validation for JS/TS/Java/C#)

## Inputs
- `src/launcher/workers/understand/extract/_snippets.py` — `_extract_snippets()` function
- `src/launcher/models/claims.py` — `Snippet` model

## Outputs
- Updated `_snippets.py` with import validation step
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-07_snippet-import-path-validation.md
- src/launcher/workers/understand/extract/_snippets.py
- tests/unit/workers/understand/test_snippet_claim_extraction.py

### Allowed paths rationale
Only _snippets.py changes. Tests in existing snippet test file.

## Implementation steps

### Step 1: Add _validate_snippet_imports() helper
Add to `_snippets.py`:
```python
def _validate_snippet_imports(
    snippets: list["Snippet"],
    import_allowlist: list[str],
) -> tuple[list["Snippet"], int]:
    """Validate snippet import lines against import_allowlist.

    Returns (valid_snippets, invalid_count).
    Only validates Python snippets. Non-Python snippets pass through.
    """
    if not import_allowlist:
        return snippets, 0

    import re
    valid, invalid_count = [], 0
    for snippet in snippets:
        if snippet.language not in ("python", "py", ""):
            valid.append(snippet)  # non-Python passes through
            continue
        # Extract import paths from the snippet code
        imports_in_code = re.findall(
            r'(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))',
            snippet.code,
        )
        import_paths = [p for pair in imports_in_code for p in pair if p]
        if not import_paths:
            valid.append(snippet)  # no imports → pass through
            continue
        # Check if any import path matches allowlist
        allowlist_set = set(import_allowlist)
        # Also check prefix matching (aspose.threed.scene matches aspose.threed)
        def _import_allowed(imp: str) -> bool:
            if imp in allowlist_set:
                return True
            return any(imp.startswith(a) or a.startswith(imp) for a in allowlist_set)

        if all(_import_allowed(imp) for imp in import_paths):
            valid.append(snippet)
        else:
            invalid_count += 1
            logger.debug(
                "snippet_import_invalid: imports=%s not in allowlist=%s",
                import_paths[:3], import_allowlist[:3],
            )

    return valid, invalid_count
```

### Step 2: Call validation in _entry.py after snippet extraction
In `run_extract()` after `snippets = _extract_snippets(...)`:
```python
# TC-HAL-07: validate snippet import paths
invalid_import_count = 0
try:
    from launcher.workers.understand.extract._snippets import _validate_snippet_imports
    snippets, invalid_import_count = _validate_snippet_imports(
        snippets, api_surface.import_allowlist or []
    )
    if invalid_import_count:
        logger.warning(
            "snippet_import_validation: %d snippets filtered (invalid import path)",
            invalid_import_count,
        )
except Exception:
    logger.warning("snippet_import_validation failed", exc_info=True)
```

### Step 3: Unit tests
Add to `tests/unit/workers/understand/test_snippet_claim_extraction.py`:
- `test_snippet_valid_import_kept` — snippet with `from aspose.threed import Node`, allowlist contains "aspose.threed" → kept
- `test_snippet_invalid_import_filtered` — snippet with `from aspose.threed import Node`, allowlist contains only "aspose_3d_foss" → filtered
- `test_non_python_snippet_passes` — Java/C# snippet → always passes
- `test_no_imports_snippet_passes` — Python snippet with no import lines → passes
- `test_empty_allowlist_passes_all` — empty allowlist → all snippets pass

## Failure modes

### Failure mode 1: Valid snippets incorrectly filtered (false positive)
**Detection**: Import path `aspose.threed.scene` doesn't match allowlist `aspose.threed` exactly
**Resolution**: Use prefix matching: `aspose.threed.scene`.startswith(`aspose.threed`) → allowed
**Gate**: Unit test with submodule import path

### Failure mode 2: import_allowlist not populated
**Detection**: `api_surface.import_allowlist` is empty → validation skips (returns all snippets)
**Resolution**: Graceful degradation — if allowlist unavailable, all snippets pass. Log at debug level.
**Gate**: Unit test with empty allowlist → 0 filtered

### Failure mode 3: Non-standard import styles
**Detection**: `import aspose; aspose.threed.Node(...)` — package aliasing
**Resolution**: Regex catches `import aspose` → checks against allowlist. `aspose` prefix match with `aspose.threed` allowlist entry depends on whether we check prefix in EITHER direction. The `a.startswith(imp) or imp.startswith(a)` handles this.
**Gate**: Manual check on test fixtures

## Task-specific review checklist
1. [ ] Only validates Python snippets (language check)
2. [ ] Empty import_allowlist → all snippets pass (safe degradation)
3. [ ] Prefix matching handles submodule imports
4. [ ] `invalid_import_count` logged at WARNING level
5. [ ] Unit test: valid import → kept
6. [ ] Unit test: invalid import → filtered
7. [ ] Unit test: non-Python → passes

## Deliverables
1. Updated `src/launcher/workers/understand/extract/_snippets.py`
2. Unit tests
3. `reports/TC-HAL-07/evidence.md`

## Acceptance checks
1. [ ] `test_snippet_valid_import_kept` PASS
2. [ ] `test_snippet_invalid_import_filtered` PASS
3. [ ] `test_non_python_snippet_passes` PASS
4. [ ] Full test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_snippet_claim_extraction.py -v
```

## Integration boundary proven
**Upstream**: `_extract_snippets()` produces raw snippets
**Downstream**: Filtered snippets passed to section_prompt.py for code injection
**Contract**: `Snippet.source_type` and `api_surface.import_allowlist` fields
