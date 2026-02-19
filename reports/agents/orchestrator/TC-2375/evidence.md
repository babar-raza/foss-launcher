# Evidence: TC-2375 — RD-02 Zone-Aware AST Content Parser

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Branch:** `healing/blkr-01-03-04-rd06`
**Status:** Done

---

## Summary

Created `markdown_zones.py` — a zone-aware markdown parser that splits documents into
typed zones (FRONTMATTER, CODE_FENCE, HEADING, TABLE, LIST, PROSE). Added
`apply_to_prose_zones()` helper and wrapped 5 pure-prose sanitizers in
`content_sanitizer.py`'s `run_pipeline()` to prevent code blocks and frontmatter
from being accidentally mutated by prose rules.

---

## Root Cause

`content_sanitizer.py` had 45+ regex sanitizers applied to ALL content. Several functions
(e.g., `strip_emojis`, `strip_double_periods`, `normalize_module_names`) could inadvertently
modify content inside code blocks (e.g., replacing `..` which is valid Python, or removing
emojis from code string literals). The cascading-fix-breaks-other-fix pattern traced back to
this root cause across multiple rounds.

---

## Implementation

### `markdown_zones.py` (new)

- `Zone` dataclass: `zone_type: str`, `content: str`, `start_line: int`
- `parse_zones(text: str) -> List[Zone]`: line-based state machine using `splitlines(keepends=True)` for exact round-trip
- `render_zones(zones: List[Zone]) -> str`: joins zone contents in order
- `apply_to_prose_zones(fn, content) -> str`: applies `fn` to all non-FRONTMATTER, non-CODE_FENCE zones
- Round-trip invariant: `render_zones(parse_zones(text)) == text` guaranteed for all inputs
- Zone type constants: `FRONTMATTER`, `CODE_FENCE`, `HEADING`, `TABLE`, `LIST`, `PROSE`

### `content_sanitizer.py` (updated)

Import: `from .markdown_zones import apply_to_prose_zones`

5 sanitizers in `run_pipeline()` Phase 4 wrapped with zone guard:

| Sanitizer | Reason for wrapping |
|-----------|---------------------|
| `strip_boilerplate_sentences` | Should not strip boilerplate from code comments |
| `strip_inline_seo_keywords` | SEO keyword patterns in code variable names should be preserved |
| `strip_double_periods` | `..` is valid Python (relative import); must not be stripped from code |
| `strip_emojis` | Emoji in code string literals is valid and should be preserved |
| `normalize_module_names` | Product module names in code blocks should remain verbatim |

Phase 2 fence-normalization functions (12 functions) are NOT wrapped — they explicitly need cross-zone context to repair fence structure.

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/_shared/markdown_zones.py` | New file: Zone dataclass + parse_zones + render_zones + apply_to_prose_zones |
| `src/launch/workers/_shared/content_sanitizer.py` | Import `apply_to_prose_zones`; wrap 5 sanitizers in `run_pipeline()` |
| `tests/unit/workers/test_content_sanitizer.py` | 11 new zone tests in `TestMarkdownZones` class |
| `specs/21_worker_contracts.md` | Added "Shared Module: Zone-Aware Sanitizer Model" section |

---

## Test Results

```
TestMarkdownZones: 11/11 pass
  - test_roundtrip_plain_prose
  - test_roundtrip_with_frontmatter
  - test_roundtrip_with_code_fence
  - test_roundtrip_multiple_fences
  - test_roundtrip_no_trailing_newline
  - test_frontmatter_zone_type
  - test_code_fence_zone_type
  - test_prose_zone_type
  - test_apply_does_not_modify_code_fence
  - test_apply_does_not_modify_frontmatter
  - test_apply_modifies_prose_zones

Full content_sanitizer suite: 510/510 pass (no regressions)
Full suite: 4575 passed, 9 skipped, 0 failed
```

---

## Acceptance Criteria

| Check | Result |
|-------|--------|
| Round-trip identity on 5 fixture strings | ✅ |
| FRONTMATTER zone correctly isolated | ✅ |
| CODE_FENCE zone correctly isolated | ✅ |
| `apply_to_prose_zones` does NOT modify CODE_FENCE content | ✅ |
| `apply_to_prose_zones` does NOT modify FRONTMATTER content | ✅ |
| 5 wrapped sanitizers: existing tests still pass (510/510) | ✅ |
| Full suite: 0 failures | ✅ 4575/4575 |
