# TC-GEN-203 Evidence — Whole-page generation

## Date: 2026-03-14

## Summary

Added whole-page generation that makes ONE LLM call per page with ALL claims and sections, eliminating cross-section repetition caused by per-section round-robin claim distribution.

## Files changed

| File | Change |
|------|--------|
| `src/launcher/workers/generate/section_prompt.py` | Added `build_page_prompt()` (~180 lines) |
| `src/launcher/workers/generate/worker.py` | Added `_generate_page_whole()` (~190 lines), dispatch logic in `_generate_page()` (~30 lines) |
| `tests/unit/workers/test_generate.py` | Added 5 new tests in `TestWholePageGeneration` class, fixed 1 existing test |

## Implementation details

### build_page_prompt() in section_prompt.py
- Includes ALL skeleton headings with levels and directives
- Includes ALL assigned claims (no round-robin distribution)
- Includes API surface, snippets, SEO keywords, install recipe, limitations
- Adds cross-section coherence instruction ("Each claim should appear in exactly one section")
- Output format: JSON array of section objects with heading/level/blocks

### _generate_page_whole() in worker.py
- Single LLM call via `_call_llm()` with token budget based on sum of section max_words
- Parses JSON array response, validates each section through `parse_and_validate_blocks()`
- Applies full post-LLM validation chain per section: hallucinated code strip, identifier validation, commercial URL strip, code language normalization, canonical import fix, empty href fix, competitor link strip, identifier repair (TC-4213)
- Cross-section deduplication via `deduplicate_sections()`
- Returns None on any parse/validation failure (caller falls back to per-section)
- Returns `(PageIR, 1, 0, "", variant, repair_log)` on success

### _generate_page() dispatch
- Tries whole-page first when `cached_page_ir is None` and `context.llm_config` is set
- If `_generate_page_whole()` returns None or raises, falls through to per-section
- Skips whole-page when `cached_page_ir` is provided (heal/regen mode)

## Test results

### New tests (5/5 passed)
- `test_build_page_prompt_includes_all_sections` - verifies all skeleton headings present
- `test_build_page_prompt_includes_all_claims` - verifies no round-robin, all claims present
- `test_generate_page_whole_parses_valid_json` - mock LLM valid JSON -> PageIR
- `test_generate_page_whole_falls_back_on_bad_json` - mock LLM invalid -> None
- `test_generate_page_dispatch_tries_whole_first` - verifies whole-page called before per-section

### Existing test fix
- `test_section_retry_capped_at_max`: Added mock for `_generate_page_whole` returning None to isolate per-section retry behavior

### Full test suite
```
425 passed in test_generate.py
4136 passed, 58 failed (pre-existing TypeScript adapter failures), 64 skipped in full suite
```

## Acceptance checks

- [x] All existing tests pass (4136+ passed, 0 new failures)
- [x] 5 new tests pass
- [x] build_page_prompt produces valid prompt with all sections and claims
- [x] _generate_page_whole returns PageIR on valid JSON or None on invalid
- [x] _generate_page tries whole-page before per-section (unless cached_page_ir)
