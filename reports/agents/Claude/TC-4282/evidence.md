# TC-4282 Evidence: Generate double-foss string-level fallback

## Root Cause

`normalize_imports_ast()` in `ts_analyzer.py` imports successfully (no `ImportError`) even when tree-sitter is unavailable. Without tree-sitter, it falls back to regex-based `normalize_imports()` which uses the hyphen-blind pattern `(@aspose/\w+)`. This regex truncates `@aspose/3d-foss` to `@aspose/3d`, then replaces, producing cascading `-foss` suffixes:

- Input: `@aspose/3d-foss-foss` (double-suffix from LLM)
- After regex fallback: `@aspose/3d-foss-foss-foss` (triple-suffix — WORSE)

## Fix

Added string-level fallback in `section_validator.py` (line 394-402) AFTER the AST normalization block. Uses a `while` loop to handle cascading suffixes:

```python
canonical_import = product.canonical_import
if canonical_import and "-foss" in canonical_import:
    _double = canonical_import + "-foss"
    while _double in content:
        content = content.replace(_double, canonical_import)
```

- Zero false-positive risk: `canonical_import + "-foss"` can never be legitimate
- Idempotent: no-op when content already correct
- Handles cascading: `while` loop reduces triple→double→single

## Tests

2 new tests in `TestDoubleFossCanonicalImportFallback`:
1. `test_double_suffix_replaced` — verifies `@aspose/3d-foss-foss` → `@aspose/3d-foss`
2. `test_no_double_suffix_unchanged` — verifies correct imports pass through unchanged

## Impact

Eliminates `canonical_import` failures on all 21 3D TypeScript pages (100% of pages affected).
