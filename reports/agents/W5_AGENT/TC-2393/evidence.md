# TC-2393 Evidence: Code-First Assembly for W5 SectionWriter

**Taskcard**: TC-2393
**Owner**: W5_AGENT
**Date**: 2026-02-20
**Status**: Done

## Files Created / Modified

### New file: `src/launch/workers/w5_section_writer/code_generator.py`

Complete implementation of the code-first generation module:

- `CodeBlock` dataclass: `label`, `language`, `code`, `explanation`, `api_refs_used`, `is_valid`, `validation_issues`
- `generate_code_block(section_title, api_context, llm_client, language, temperature=0.05) -> CodeBlock`
  - Infers language from API context if not specified
  - Calls `llm_client.chat_completion` with API-only context at `temperature=0.05`
  - Gracefully handles LLM failures: returns placeholder `CodeBlock` with `is_valid=False`
  - Calls `_validate_code_static()` to detect unbalanced parens and placeholder text
- `normalize_assembled_content(content: str) -> str`
  - Pure function (no I/O, no LLM calls)
  - Deduplicates consecutive `##` / `###` headings (handles blank lines between duplicates)
  - Infers fence language: `using Aspose` / `namespace` / `Install-Package` → csharp; `import` / `def` / `pip install` → python
  - Leaves already-tagged fences unchanged
- `_validate_code_static(code, api_refs) -> List[dict]`
  - Checks unbalanced parentheses (critical)
  - Checks placeholder markers: `TODO`, `YOUR_CODE`, `...`, `PLACEHOLDER` (critical)
  - Checks that at least one API method from context appears in code (minor)
- `_infer_language(api_context)` — detects C#/Python from context text
- `_extract_code_and_lang(raw, default_lang)` — extracts code and language from fenced LLM response
- `_extract_api_refs_used(code, api_refs)` — returns which API refs appear in generated code

### Modified: `src/launch/workers/w5_section_writer/multi_pass.py`

Integration changes (additive only, no existing logic changed):

1. **Import block** (lines 32-36): Added `from launch.workers.w5_section_writer.code_generator import CodeBlock, generate_code_block, normalize_assembled_content`

2. **`_generate_draft()` — code-first pass** (new preamble before prose generation):
   - Identifies sections whose headings contain: `install`, `example`, `usage`, `start`, `basic`, `code`
   - For each such section, gathers API signatures from assigned claims (claim_text containing `(`)
   - Calls `generate_code_block(heading, api_sigs, self.llm_client)` at temperature 0.05
   - Stores results in `code_sections: Dict[str, Any]` dict
   - Injects pre-generated code blocks into `prompt_vars["pre_generated_code_blocks"]` so the prose writer places them first
   - Entire code-first pass is wrapped in `try/except` — failures are non-fatal warnings

3. **`generate()` — normalize after assembly**:
   - After thin-page (skip refinement) path: calls `normalize_assembled_content(draft)`
   - After refinement path: calls `normalize_assembled_content(refined)`

### Modified: `tests/unit/workers/test_tc_440_section_writer.py`

Added `class TestCodeFirstAssembly` with 6 tests:

| Test | Assertion |
|------|-----------|
| `test_generate_code_block_valid` | Mock LLM returns valid Python → `is_valid=True` |
| `test_generate_code_block_placeholder_invalid` | Mock returns `# TODO: placeholder` → `is_valid=False` |
| `test_normalize_duplicate_headings` | `## Installation` × 3 → collapses to 1 |
| `test_normalize_fence_language_python` | `` ``` `` with `import` → `` ```python `` |
| `test_normalize_fence_language_csharp` | `` ``` `` with `using Aspose` → `` ```csharp `` |
| `test_normalize_fence_already_tagged` | `` ```python `` → unchanged, count=1 |

## Test Results

```
6/6 new TC-2393 tests: PASS
Full suite: 4620 passed, 9 skipped, 0 failed (190s)
```

Previous baseline: 4614 passed, 9 skipped (TC-2393 added 6 new tests).

## Acceptance Checks Verified

- [x] `code_generator.py` created with `CodeBlock` dataclass, `generate_code_block()`, `normalize_assembled_content()`
- [x] Static validation catches: unbalanced parens (`(` count != `)` count), placeholder text (`TODO`, `YOUR_CODE`, `...`, `PLACEHOLDER`)
- [x] `normalize_assembled_content()` deduplicates consecutive headings (including blank-line-separated duplicates)
- [x] Language inference: `using Aspose` → csharp, `import` → python
- [x] All 6 tests pass; full suite has 0 regressions (4620 passed)
- [x] Integration in `multi_pass.py` calls code generator before prose for code-heavy sections
- [x] `generate_code_block()` gracefully handles LLM failures (returns placeholder CodeBlock with `is_valid=False`)
- [x] `normalize_assembled_content()` is pure (no LLM calls, no I/O)
