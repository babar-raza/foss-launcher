# BT-01: Fix Table Block Ordering Bug

**Status**: Done
**Gap linkage**: BT-00 → BT-01
**Role**: Engineer
**Severity**: HIGH — backticks applied to raw JSON content that then gets restructured, losing the insertions

## Problem

In `section_validator.py:_validate_block()`, the backtick pass (`_backtick_api_names`) runs at line 237-238 BEFORE `_validate_table_content()` at line 241-242. For table blocks whose LLM output is a JSON array of dicts (not yet pipe-delimited markdown), backticks are applied to raw JSON that then gets completely restructured by `_validate_table_content()` → `_json_array_to_markdown_table()`, discarding the backtick insertions.

## Scope

**In scope**: Reorder the two calls in `_validate_block()` so table validation happens first.
**Out of scope**: Any other block type ordering, new features.

## Fix

In `_validate_block()` (section_validator.py), move the table validation block BEFORE the backtick/prose normalization block:

```python
# Current (WRONG for tables):
#   1. _sanitize_html_links
#   2. _strip_claim_citations
#   3. _normalize_product_name
#   4. _backtick_api_names        ← runs on raw JSON for tables
#   5. _validate_table_content    ← restructures content, losing backticks

# Fixed:
#   1. _validate_table_content    ← normalize table format first
#   2. _sanitize_html_links
#   3. _strip_claim_citations
#   4. _normalize_product_name
#   5. _backtick_api_names        ← now runs on pipe-delimited markdown
```

## Acceptance Checks

- [ ] `_validate_table_content()` runs BEFORE `_backtick_api_names()` for table blocks
- [ ] Unit test: table block with JSON array content containing API names → backticks present in final pipe-delimited output
- [ ] Unit test: table block with already-pipe-delimited content → backticks applied correctly
- [ ] Existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`

## Deliverables

- Modified: `src/launcher/workers/generate/section_validator.py`
- New test(s) in: `tests/test_section_validator.py` (or appropriate test file)

## Hard Rules

- Do NOT change the ordering for non-table block types
- Do NOT add new parameters or change function signatures
- Preserve all existing behavior for paragraph, code, heading, list, callout blocks

## Review Dimensions

1. Table content with JSON arrays: backticks survive restructuring
2. Table content already pipe-delimited: backticks applied correctly
3. Non-table blocks: ordering unchanged, behavior identical
4. Edge case: empty table content — no crash

## Now (Runbook)

1. Read `section_validator.py:_validate_block()` (lines 205-276)
2. Move the `if block_type == BlockType.table:` block (lines 241-242) to execute BEFORE the prose normalization block (lines 233-238)
3. Write regression test with JSON-array table content containing API names
4. Run full test suite
