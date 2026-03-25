# TC-NEW-002 Evidence — Docstring Return Type Extraction

## Date: 2026-03-16

## Changes Made

### 1. `src/launcher/shared/code_analyzer.py`
- Added `_extract_return_type_from_docstring()` function
  - Parses Google-style (`Returns:\n    Type: description`)
  - Parses Google-style inline (`Returns: Type`)
  - Parses NumPy-style (`Returns\n-------\nType`)
  - Parses Sphinx-style (`:rtype: Type`)
  - `_clean_type_string()` helper rejects prose-like results
- Modified `_extract_return_annotation()` to use docstring fallback
  - When AST annotation is absent, calls `_extract_return_type_from_docstring()`

### 2. `src/launcher/workers/generate/worker.py`
- Fixed `_render_methods_section()` line 947
  - Old: `ret = m.return_type or "None"` → always showed `→ None`
  - New: `ret = m.return_type` + conditional arrow display
  - Methods with known return type: `**method**(params) → Type`
  - Methods with unknown return type: `**method**(params)` (no misleading → None)

## Test Results

```
11 new tests in TestExtractReturnTypeFromDocstring:
- test_sphinx_rtype ✓
- test_sphinx_rtype_dotted ✓
- test_google_style_indented ✓
- test_google_style_inline ✓
- test_google_style_optional ✓
- test_numpy_style ✓
- test_no_returns_section ✓
- test_empty_docstring ✓
- test_none_docstring ✓
- test_rejects_prose_description ✓
- test_list_type ✓
```

## Full Suite Regression

```
4827 passed, 64 skipped, 3 xfailed, 2 xpassed (0 failures)
```

## Root Cause Chain (verified)

```
Python Source (no annotations) → _extract_return_annotation() returns ""
→ method_details["return_type"] = "" → MethodSignature(return_type="")
→ worker.py: ret = "" or "None" = "None" → "→ None" rendered
```

## Expected E2E Impact

- Reference pages no longer show "→ None" for every method
- Methods with docstring type info now show correct return types
- Methods without type info show clean signature without misleading arrow
- Estimated A+B lift: +2-5pp on reference pages
