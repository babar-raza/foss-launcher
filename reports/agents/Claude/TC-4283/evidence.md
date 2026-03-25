# TC-4283 Evidence: Understand non-canonical snippet import filtering

## Root Cause

`_normalize_snippet_imports()` in `_snippets.py` only blocked imports matching `_KNOWN_NON_FOSS_MODULES` (frozenset `{"pydrawing"}`). Non-canonical single-word product imports like `from onenote import Document` passed through because:

1. `onenote` is not in `_KNOWN_NON_FOSS_MODULES`
2. `onenote` doesn't match any `rewrite_prefixes` (which check for `aspose.*` patterns)
3. `_validate_snippet_imports` downstream considers snippets without product imports as valid

These contaminated snippets were passed to Generate as "REAL USAGE PATTERNS", causing the LLM to reproduce `from onenote import Document` verbatim.

## Fix

Added `_is_stdlib_module()` helper using `sys.stdlib_module_names` and a new check in `_normalize_snippet_imports()` (after the rewrite prefix matching fails). When a single-word module (no dots) is:
- NOT in the product's canonical/runtime import roots
- NOT a stdlib module
- NOT already handled by `_KNOWN_NON_FOSS_MODULES`

...the import line is dropped with a debug log.

## Tests

3 new tests in `TestNonCanonicalSnippetImportFilter`:
1. `test_non_canonical_import_dropped` — `from onenote import Document` → line dropped
2. `test_canonical_import_preserved` — `from aspose.note import Document` → preserved
3. `test_stdlib_import_preserved` — `import os`, `import json` → preserved

## Impact

Eliminates `canonical_import` and `code` findings caused by `from onenote import Document` contamination in Note Python (2+ pages with `api-overview` findings).
