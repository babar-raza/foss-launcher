# TC-GEN-204: Reference Pages from ClassBrief Data — Evidence

## Status: COMPLETE

## Changes Made

### src/launcher/workers/generate/worker.py

Added 6 new functions (all deterministic, zero LLM calls):

1. **`_find_class_brief(target_class, class_briefs)`** — Looks up a ClassBrief by exact name match. Returns None on miss.

2. **`_render_overview_section(class_brief, product)`** — Builds SectionIR from docstring_snippet or fallback text.

3. **`_render_properties_section(class_brief)`** — Builds a table SectionIR from typed_properties. Returns None if empty.

4. **`_render_methods_section(class_brief)`** — Builds paragraph blocks per method with signature and docstring. Returns None if empty.

5. **`_render_enum_section(class_brief)`** — Builds list blocks per enum with member names. Returns None if empty.

6. **`_generate_reference_page(page_plan, product, class_briefs, context)`** — Async entry point that assembles a complete PageIR from ClassBrief data. Returns None when no matching brief or insufficient content, allowing fallthrough to standard LLM path.

Added dispatch in `_generate_page()` (after frontmatter merge, before claim filtering):
- For `reference_object_page` or `api_reference` roles with a `target_class`, calls `_generate_reference_page()`.
- If it returns None, the standard LLM path runs as before.

### tests/unit/workers/test_generate.py

Added 16 new tests across 6 test classes:

| Class | Tests | Validates |
|-------|-------|-----------|
| TestFindClassBrief | 4 | found, not found, None briefs, empty target |
| TestRenderPropertiesSection | 2 | table output, None on empty |
| TestRenderMethodsSection | 2 | paragraph output, None on empty |
| TestRenderEnumSection | 2 | list output, None on empty |
| TestRenderOverviewSection | 2 | with/without docstring |
| TestGenerateReferencePage | 4 | empty brief -> None, full brief -> PageIR, no match -> None, no target -> None |

## Test Results

- **test_generate.py**: 436 passed (420 existing + 16 new), 0 failed
- **Full suite** (excluding pre-existing collection error in test_clone.py): 4147 passed, 58 failed (all pre-existing in test_typescript_adapter.py), 64 skipped

## Key Design Decisions

- **Deterministic only**: Zero LLM calls for reference pages. Content comes directly from AST-extracted ClassBrief data.
- **Graceful fallthrough**: Returns None when ClassBrief is missing/empty, so the existing claim-based path handles edge cases.
- **No code removed**: The dispatch is purely additive. All existing generation paths remain intact.
- **Return shape matches**: Same 6-tuple as `_generate_page()` for seamless integration with the caller in `_process_page`.
