# TC-3701 Implementation Report: PageIR Schema + Deterministic Markdown Renderer

**Date**: 2026-03-04
**Agent**: agent_b2
**Taskcard**: TC-3701
**Status**: COMPLETE

---

## Files Created

| File | Type | Purpose |
|------|------|---------|
| `src/launch/workers/_shared/page_ir.py` | NEW | PageIR Pydantic schema (BlockIR, SectionIR, PageIR) |
| `src/launch/workers/_shared/ir_renderer.py` | NEW | Deterministic PageIR -> Markdown renderer |
| `tests/unit/workers/shared/__init__.py` | NEW | Package marker (empty) |
| `tests/unit/workers/shared/test_page_ir_schema.py` | NEW | 12 schema tests |
| `tests/unit/workers/shared/test_ir_renderer.py` | NEW | 15 renderer tests |

---

## Test Evidence

### New test run (TC-3701 tests only)

```
PYTHONHASHSEED=0 python -m pytest tests/unit/workers/shared/ -v
27 passed, 1 warning in 1.09s
```

### All tests (excluding pre-existing worktree failures)

```
PYTHONHASHSEED=0 python -m pytest tests/ (excluding 5 pre-existing worktree files)
8555 passed, 13 skipped, 3 xfailed, 19 warnings in 165.18s
```

### Pre-existing worktree failures (NOT caused by TC-3701)

The following test files fail in the worktree due to the plans/taskcards/ directory not being
fully synced (e.g., TC-100 taskcard exists in main repo but not in worktree):
- `tests/unit/io/test_atomic_taskcard.py` (2 failures - TC-100 not in worktree plans/)
- `tests/unit/util/test_taskcard_loader.py` (5 failures - same root cause)
- `tests/unit/orchestrator/test_run_loop_taskcard.py` (1 failure)
- `tests/unit/workers/w9/test_gate_fixtures.py` (4 failures - fixture files not in worktree)
- `tests/unit/test_validation_engine_golden.py` (1 failure - golden fixture not in worktree)

Confirmed: all these tests pass in the main repo (`64 passed` for the taskcard/fixture tests).

---

## Test Breakdown

### test_page_ir_schema.py (12 tests)

| Test | Class | Description |
|------|-------|-------------|
| test_block_ir_paragraph_valid | TestBlockIR | Valid paragraph block created with defaults |
| test_block_ir_list_valid | TestBlockIR | List content stored as list |
| test_block_ir_code_python_valid | TestBlockIR | Valid Python code passes AST check |
| test_block_ir_code_python_invalid_raises | TestBlockIR | Invalid Python raises ValidationError |
| test_block_ir_code_no_lang_skips_ast | TestBlockIR | Non-Python lang skips AST validation |
| test_block_ir_invalid_type_raises | TestBlockIR | Unknown block_type raises ValidationError |
| test_section_ir_valid | TestSectionIR | Valid section with heading and blocks |
| test_page_ir_valid_full | TestPageIR | Full page schema_version defaults to "1.0" |
| test_page_ir_schema_version_default | TestPageIR | schema_version default confirmed |
| test_validate_claim_attribution_finds_empty | TestPageIR | Factual block without claim_ids detected |
| test_validate_claim_attribution_passes_with_ids | TestPageIR | Block with claim_ids passes |
| test_page_ir_json_round_trip | TestPageIR | model_dump_json / model_validate_json round-trip |

### test_ir_renderer.py (15 tests)

| Test | Class | Description |
|------|-------|-------------|
| test_render_paragraph_block | TestRenderBlocks | Paragraph content + trailing \n\n |
| test_render_list_block | TestRenderBlocks | List items with "- " prefix |
| test_render_code_block_python | TestRenderBlocks | ``` python fenced block |
| test_render_code_block_no_lang | TestRenderBlocks | Code without lang uses "text" fence |
| test_render_table_block | TestRenderBlocks | Table with pipe separator + --- row |
| test_render_links_block | TestRenderBlocks | Links rendered as list items |
| test_render_callout_block | TestRenderBlocks | Callout with "> " prefix |
| test_render_section_adds_heading | TestRenderSection | ## heading added |
| test_render_blank_line_after_heading | TestRenderSection | ## heading\n\n present |
| test_render_page_frontmatter | TestRenderPage | Output starts with ---\n |
| test_render_full_page_no_double_newlines | TestRenderPage | No \n\n\n sequences |
| test_render_deterministic | TestRenderPage | Same input yields same output twice |
| test_render_empty_sections_list | TestRenderPage | Empty sections still renders frontmatter |
| test_render_code_fence_language_tag_present | TestRenderPage | ``` python in full page |
| test_render_table_has_separator_row | TestRenderPage | --- separator in table output |

---

## Design Decisions

1. **Pydantic v2**: Used `field_validator`, `model_validator(mode="after")`, `model_dump_json()`,
   `model_validate_json()` — all pydantic v2 APIs. Version confirmed: 2.12.5.

2. **YAML fallback**: `ir_renderer.py` uses try/except for yaml import with a fallback
   dict-to-string implementation so the module never fails if yaml is unavailable.

3. **Python AST validation**: Only triggered when `block_type="code"` AND `lang="python"`.
   Non-Python languages skip AST checking entirely.

4. **Triple-newline guard**: `render_page()` normalizes `\n\n\n` to `\n\n` in a loop
   to ensure deterministic output regardless of block content.

5. **Table rendering**: First row is treated as header. Separator row (`---`) is always
   inserted. Cells are padded to header column count.

6. **Code block default lang**: `block.lang or "text"` ensures fenced code always has
   a language tag — eliminates linting warnings from bare ``` fences.
