# TC-2395 Evidence: SEO Hardening — keyword_utils.py

**Taskcard**: TC-2395
**Owner**: W6_AGENT
**Date**: 2026-02-20
**Status**: Done

## Summary

Implemented TC-2395: SEO hardening with keyword extraction from content, natural injection with
1.5% density cap, and metadata quality enforcement for the W6 SEO Optimizer worker.

## Files Created / Modified

### New File: `src/launch/workers/w6_seo_optimizer/keyword_utils.py`

Contains 4 functions adapted from content-generator patterns:

1. `extract_keywords_from_content(content, max_keywords=10)` — heuristic TF-IDF-style keyword
   extraction from page content. Strips frontmatter, excludes stopwords, prefers proper nouns
   (capitalized words with frequency >= 2).

2. `inject_keywords_naturally(content, keywords, max_density=0.015)` — injects keywords at
   paragraph boundaries if current density is below half the max (0.75%). Respects the 1.5%
   density cap from the content-generator standard.

3. `enforce_seo_metadata_quality(meta, content, title="")` — enforces three quality rules:
   - `seoTitle != title` (adds " | Guide" or truncates+ellipsis differentiator)
   - `description` 50-160 chars (extracts from content sentences 2-4 if too short)
   - Truncates description to 160 chars if over limit

4. `_inject_at_paragraph_boundary(content, keyword)` — internal helper that finds the first
   suitable paragraph (non-heading, non-code, >20 words, not already containing keyword) and
   prepends "When working with {keyword}, ..." phrase.

### Modified File: `src/launch/workers/w6_seo_optimizer/worker.py`

Integration points added:
- Import of `extract_keywords_from_content`, `inject_keywords_naturally as inject_kw_naturally`,
  `enforce_seo_metadata_quality` from `keyword_utils`
- Content-based keyword extraction merged with existing `extract_keywords()` output as supplementary
  source (content-generator priority: config > LLM > heuristic)
- Density-enforced injection via `inject_kw_naturally()` after existing injection pass
- Quality enforcement via `enforce_seo_metadata_quality()` after `optimize_seo_metadata()` call
- Two helper functions added to `worker.py`: `_get_seo_field()`, `_update_seo_field()`

### Modified File: `tests/unit/workers/test_w6_seo_optimizer.py`

Added `TestKeywordUtils` class with 9 tests covering:
- `test_extract_keywords_from_content` — returns list of strings, max length respected
- `test_extract_keywords_excludes_stopwords` — STOPWORDS not in output
- `test_inject_keywords_respects_density` — high-density keyword not injected again
- `test_inject_keywords_below_threshold` — absent keyword is injected at paragraph boundary
- `test_enforce_seo_metadata_quality_seotitle_differs` — identical seoTitle/title is differentiated
- `test_enforce_seo_metadata_quality_desc_length` — short description extracted from content
- `test_enforce_seo_metadata_quality_desc_truncated` — 200-char description truncated to <=160
- `test_inject_at_paragraph_boundary_injects` — keyword injected into suitable paragraph
- `test_inject_at_paragraph_boundary_skips_code` — code block paragraphs not injected

## Test Results

```
4653 passed, 9 skipped, 0 failed, 1 warning in 218.71s
```

Previous: 4620 passed (per task description expectation). Delta: +33 tests (9 in TestKeywordUtils
class + pre-existing growth from other work in the suite run).

W6 test file specifically: 67 passed, 1 warning in 1.73s.

## Acceptance Checklist

- [x] `keyword_utils.py` created with 3 functions + `_inject_at_paragraph_boundary`
- [x] W6 uses content-extracted keywords as supplementary source
- [x] Keyword density capped at 1.5% (`max_density=0.015`)
- [x] seoTitle != title enforced (adds " | Guide" or truncates)
- [x] description 50-160 chars enforced (extracts from content sentences 2-4)
- [x] All 9 new tests pass; full suite has 0 regressions
